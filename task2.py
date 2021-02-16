import random

import simpy


class Roundabout(object):
    def __init__(self, env, size):
        self.env = env
        self.size = size
        self.space = simpy.Resource(env, capacity=size) # roundabout resource

        self.lock = simpy.Resource(env, capacity=1)     # mutex for resources below
        self.next_exit = None                           # { 'dir' }
        self.occupying_cars = []                        # { 'exit_dir' : time of exit }

    # from car: ( entry_lane )
    def request_enter(self, entry_lane, name):

        if self.space.count >= self.size:               # if occupied
            with self.lock.request() as updater:
                #yield updater
                n_exit = self.next_exit

            if n_exit == entry_lane:
                print("car {}\t entry approved at {}: ".format(name,env.now), self.space.count)
                return True

        else:                                           # if space
            print("car {}\t entry approved at EMPTY {}: ".format(name, env.now), self.space.count)
            return True

        return False

    # from car: ( drive_time, exit_lane, info )
    def enter(self, drive_time, exit_lane, name):
        print("car {}\t entered at: ".format(name), env.now)

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

        print("current next exit", self.next_exit)
        return info

    # from car: ( info )
    def exit(self, info, name):
        print("car {} exit at: ".format(name), env.now)
        i = 0
        temp = ()

        with self.lock.request() as updater:
            #yield updater

            self.occupying_cars.remove(info)

            for (i_dir, i_time) in self.occupying_cars:
                if i == 0:
                    temp = (i_dir, i_time)
                if temp[1] > i_time:
                    temp = (i_dir, i_time)
                i += 1

            self.next_exit = temp


# to have car as a class doesnt seem to work because you cant start the class as a process

"""
class Car:

    def __init__(self, env, roundabout, entry_lane, exit_lane, drive_time, queue):
        self.env = env
        self.roundabout = roundabout
        self.entry_lane = entry_lane
        self.exit_lane = exit_lane
        self.drive_time = drive_time
        self.car_info = ()
        self.queue = queue
        self.queue_time = env.now

        self.action = env.process(self.enter_roundabout(roundabout))

    def enter_roundabout(self, roundabout):
        request = self.queue.request()
        yield request

        while True:
            if roundabout.request_enter(self):
                with roundabout.space.request() as req:
                    yield req # should be 0 if roundabout has space

                    roundabout.enter(self)
                    self.queue.release(request)
                    yield self.env.timeout(self.drive_time)

                    roundabout.exit(self)
                    return
"""


def car(env, roundabout, entry_lane, exit_lane, drive_time, queue, name):
    print("car {}\tready at: ".format(name),env.now)
    arrive = env.now

    request = queue.request()                                       # place in queue to roundabout
    yield request

    while True:
        result = roundabout.request_enter(entry_lane, name)

        if result:                                                  # see if car can enter
            with roundabout.space.request() as req:                 # occupy space in roundabout
                yield req                                           # should be 0 if roundabout has space

                info = roundabout.enter(drive_time, exit_lane, name) # car has officially entered roundabout
                print(info)
                queue_time = env.now - arrive
                queue.release(request)
                yield env.timeout(drive_time)

                roundabout.exit(info, name)
                return queue_time
        yield env.timeout(0.2)


def drive_time_calculator(from_lane, to_lane):

    # const 5 sek in roundabout for all cars atm

    return 5


"""
this is the car generator. one will be created for each ingoing lane into the roundabout.
traffic is a function which returns the current traffic on the lane
"""


def source(env, traffic, destination, lane_name, roundabout, lane_queue):

    # unique traffic-func, destination-func, lane_name and lane_queue for each source process

    for i in range(2):
        time = traffic(env.now)
        yield env.timeout(time)

        name = "{}.".format(i) + lane_name
        # generate exit lane
        exit_lane = destination(lane_name)

        # generate drive time
        drive_time = drive_time_calculator(lane_name, exit_lane)

        env.process(car(env, roundabout, lane_name, exit_lane, drive_time, lane_queue, name))

        # generate time between entering cars.



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

