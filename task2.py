import random
import simpy


class Roundabout(object):
    def __init__(self, env, size):
        self.env = env
        self.size = size
        self.space = simpy.PriorityResource(env, capacity=size)  # roundabout resource

        self.lock = simpy.Resource(env, capacity=1)     # mutex for resources below
        self.next_exit = ('Infinte', 9999)                           # { 'dir' }
        self.occupying_cars = []                        # { 'exit_dir' : time of exit }

    # from car: ( entry_lane )
    def request_enter_priority(self, entry_lane, name):
        with self.lock.request():
            n_exit = self.next_exit

        if self.space.count >= self.size:  # if occupied
            dirs = {'north': 0, 'west': 1, 'south': 2, 'east': 3}
            entry_lane_number = dirs[entry_lane]
            exit_lane_number = dirs[n_exit[0]]
            priority = 0

            while priority < 4:
                if exit_lane_number > 3:
                    exit_lane_number = 0

                if exit_lane_number == entry_lane_number:
                    print("car {}\t was given priority: ".format(name), priority)
                    return priority, n_exit[1]

                exit_lane_number += 1
                priority += 1

        else:  # if space
            # print("car {}\t entry approved at EMPTY {}: ".format(name, env.now), self.space.count)
            return 0, n_exit[1]

    # from car: ( drive_time, exit_lane, info )
    def enter(self, drive_time, exit_lane, name):

        with self.lock.request() as updater:
            #yield updater

            time = self.env.now + drive_time
            info = (exit_lane, time)

            self.occupying_cars.append(info)

            if self.next_exit is not None:
                (curr_dir, curr_time) = self.next_exit

                if time < curr_time:
                    self.next_exit = info
            else:
                self.next_exit = info

        print("car {}\t entered at: {} ".format(name, env.now), "\tExit time is: ", time, "\tIt will exit at: ", exit_lane)
        print("Next exit", self.next_exit)
        return info

    # from car: ( info )
    def exit(self, info, name):
        # print("car {} exit at: ".format(name), env.now)
        first_time = False
        temp = ()

        with self.lock.request() as updater:
            # yield updater

            self.occupying_cars.remove(info)

            for (i_dir, i_time) in self.occupying_cars:
                if first_time is False:
                    temp = (i_dir, i_time)
                    first_time = True
                if temp[1] > i_time:
                    temp = (i_dir, i_time)

            self.next_exit = temp


def car(env, roundabout, entry_lane, exit_lane, drive_time, queue, name):
    # print("car {}\tready at: ".format(name),env.now)
    arrive = env.now

    request = queue.request()                                       # place in queue to roundabout
    yield request

    while True:
        (priority_result, next_exit_time) = roundabout.request_enter_priority(entry_lane, name)

        with roundabout.space.request(priority=priority_result) as req:
            results = yield req | env.timeout(next_exit_time - env.now)
            if req in results:
                info = roundabout.enter(drive_time, exit_lane, name)  # car has officially entered roundabout
                # print(info)
                queue_time = env.now - arrive
                queue.release(request)
                yield env.timeout(drive_time)
                roundabout.exit(info, name)
                print("car {}\t stood in queue for: ".format(name), queue_time)
                break


def drive_time_calculator(from_lane, to_lane):

    # const 5 sek in roundabout for all cars atm

    return random.randint(2,10)


"""
this is the car generator. one will be created for each ingoing lane into the roundabout.
traffic is a function which returns the current traffic on the lane
"""


def source(env, traffic, destination, lane_name, roundabout, lane_queue):

    # unique traffic-func, destination-func, lane_name and lane_queue for each source process

    for i in range(4):

        name = "{}.".format(i) + lane_name
        # generate exit lane
        exit_lane = destination(lane_name)

        # generate drive time
        drive_time = drive_time_calculator(lane_name, exit_lane)

        env.process(car(env, roundabout, lane_name, exit_lane, drive_time, lane_queue, name))

        # generate time between entering cars.
        time = traffic(env.now)
        yield env.timeout(time)


def traffic_func(time):
    r = random.random()
    t = r * 4 + 1
    return t


def destination_func(from_lane):

    l = random.choice(['north', 'west', 'south', 'east'])
    if l == from_lane:
        l = random.choice(['north', 'west', 'south', 'east'])
    return l


env = simpy.Environment()

rb = Roundabout(env, 4)
n_queue = simpy.Resource(env, capacity=1)
w_queue = simpy.Resource(env, capacity=1)
s_queue = simpy.Resource(env, capacity=1)
e_queue = simpy.Resource(env, capacity=1)
env.process(source(env, traffic_func, destination_func, 'north', rb, n_queue))
env.process(source(env, traffic_func, destination_func, 'south', rb, s_queue))
env.process(source(env, traffic_func, destination_func, 'west', rb, w_queue))
env.process(source(env, traffic_func, destination_func, 'east', rb, e_queue))
env.run()

