import random
import simpy
import matplotlib.pyplot as plt
import numpy as np

NORTH_RATE = 5
WEST_RATE = 8
SOUTH_RATE = 20
EAST_RATE = 28

ALPHA = 4  # 3.78
BETA = 0.75  # 1.3 # 1.26



class Roundabout(object):
    def __init__(self, env, size):
        self.env = env
        self.size = size
        self.space = simpy.PriorityResource(env, capacity=size)  # roundabout resource

        self.lock = simpy.Resource(env, capacity=1)     # mutex for resources below
        self.next_exit = ('north', 9999)                           # { 'dir' }
        self.occupying_cars = []                        # { 'exit_dir' : time of exit }


    def request_enter_priority(self, entry_lane):
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
                    return priority, n_exit[1]

                exit_lane_number += 1
                priority += 1

        else:  # if space
            if n_exit is not ():
                return 0, n_exit[1]
            else:
                return 0, env.now





    def enter(self, drive_time, exit_lane, name):

        with self.lock.request() as updater:
            #yield updater

            time = self.env.now + drive_time
            info = (exit_lane, time)

            self.occupying_cars.append(info)

            if self.next_exit is not ():
                (curr_dir, curr_time) = self.next_exit

                if time < curr_time:
                    self.next_exit = info
            else:

                self.next_exit = info

        #print("car {}\t entered at: {} ".format(name, env.now), "\tExit time is: ", time, "\tIt will exit at: ", exit_lane)
        #print("Next exit", self.next_exit)
        return info

    # from car: ( info )
    def exit(self, info, name):
        # print("car {} exit at: ".format(name), env.now)
        first_time = False
        temp = ()

        with self.lock.request() as updater:
            # yield updater
            car_list = self.occupying_cars.copy()
            self.occupying_cars.remove(info)

            for (i_dir, i_time) in self.occupying_cars:
                if first_time is False:
                    temp = (i_dir, i_time)
                    first_time = True
                if temp[1] > i_time:
                    temp = (i_dir, i_time)

            self.next_exit = temp


def car(env, roundabout, entry_lane, exit_lane, drive_time, queue, name):
    global QUEUE_DELAY_INTO, QUEUE_DELAY_ENTRY, NR_CARS, DRIVEN_CARS, QUEUE_DELAY_ENTRY_ARRAY, QUEUE_DELAY_INTO_ARRAY, QUEUE_DELAY_TOTAL_ARRAY
    # print("car {}\tready at: ".format(name),env.now)
    arrive = env.now

    request = queue.request()                                       # place in queue to roundabout
    yield request
    NR_CARS += 1
    arrive_entry = env.now
    QUEUE_DELAY_INTO += arrive_entry - arrive
    QUEUE_DELAY_INTO_ARRAY.append(arrive_entry - arrive)
    QUEUE_DELAY_INTO_ARRAY_X.append(env.now)

    while True:
        (priority_result, next_exit_time) = roundabout.request_enter_priority(entry_lane)

        with roundabout.space.request(priority=priority_result) as req:

            results = yield req | env.timeout((next_exit_time + 0.1) - env.now)
            if req in results:
                info = roundabout.enter(drive_time, exit_lane, name)  # car has officially entered roundabout

                QUEUE_DELAY_ENTRY += env.now - arrive_entry
                QUEUE_DELAY_ENTRY_ARRAY.append(env.now - arrive_entry)
                QUEUE_DELAY_ENTRY_ARRAY_X.append(env.now)

                QUEUE_DELAY_TOTAL_ARRAY.append(env.now - arrive)
                DRIVEN_CARS += 1
                queue.release(request)
                yield env.timeout(drive_time)
                roundabout.exit(info, name)
                print("car {}\t stood in first place for: ".format(name),env.now - arrive_entry )
                break


def drive_time_calculator(from_lane, to_lane):
    global GAMMA_TOT, GAMMA_NR
    dir_converter = {'north': 1, 'west': 2, 'south': 3, 'east': 4}
    multiplier = 1
    entry_dir = dir_converter[from_lane] + 1

    while multiplier < 4:
        if entry_dir > 4:
            entry_dir = 1

        if entry_dir == dir_converter[to_lane]:
            break
        entry_dir += 1
        multiplier += 1

    time = random.gammavariate(ALPHA, BETA)

    print(env.now ,"\t", 'drive time: {}'.format(time*multiplier))
    drive_time = time*multiplier
    return drive_time


"""
this is the car generator. one will be created for each ingoing lane into the roundabout.
traffic is a function which returns the current traffic on the lane
"""
def source(env, traffic, destination, lane_name, roundabout, lane_queue):


    # unique traffic-func, destination-func, lane_name and lane_queue for each source process
    i = 0
    while True:

        name = "{}.".format(i) + lane_name
        # generate exit lane
        exit_lane = destination(lane_name)

        # generate drive time
        drive_time = drive_time_calculator(lane_name, exit_lane)

        env.process(car(env, roundabout, lane_name, exit_lane, drive_time, lane_queue, name))

        # generate time between entering cars.

        time = random.expovariate(1 / traffic)

        #print(env.now ,"\t", 'next arrival from {} at: {}'.format(lane_name,time))
        yield env.timeout(time)

        i += 1


def destination_func(lane):
    destinations = ['north', 'west', 'south', 'east']
    destinations.remove(lane)
    l = random.choice(destinations)
    #print(env.now ,"\t", 'from: {}, to:{}'.format(lane, l))
    return l


random.seed(1337)

for i in range(1, 5):
    QUEUE_DELAY_INTO = 0
    QUEUE_DELAY_ENTRY = 0
    QUEUE_DELAY_INTO_ARRAY = []
    QUEUE_DELAY_INTO_ARRAY_X = []

    QUEUE_DELAY_ENTRY_ARRAY = []
    QUEUE_DELAY_ENTRY_ARRAY_X = []

    QUEUE_DELAY_TOTAL_ARRAY = []

    NR_CARS = 0
    DRIVEN_CARS = 0

    env = simpy.Environment()
    rb = Roundabout(env, i)

    env.process(source(env, NORTH_RATE, destination_func, 'north', rb, simpy.Resource(env, capacity=1)))
    env.process(source(env, SOUTH_RATE, destination_func, 'south', rb, simpy.Resource(env, capacity=1)))
    env.process(source(env, WEST_RATE, destination_func, 'west', rb, simpy.Resource(env, capacity=1)))
    env.process(source(env, EAST_RATE, destination_func, 'east', rb, simpy.Resource(env, capacity=1)))
    env.run(until=500)

    print('queue delay before:',QUEUE_DELAY_INTO/NR_CARS)
    print('queue delay at entry:',QUEUE_DELAY_ENTRY/DRIVEN_CARS)

    print(NR_CARS)
    print(QUEUE_DELAY_INTO)
    print(DRIVEN_CARS)
    print(QUEUE_DELAY_ENTRY)
    print("TOTAL QUEUE TIME IS: ", ((QUEUE_DELAY_INTO / NR_CARS) + (QUEUE_DELAY_ENTRY / DRIVEN_CARS)))
    '''
    plt.subplot(3,1,1)
    plt.plot(QUEUE_DELAY_INTO_ARRAY_X, QUEUE_DELAY_INTO_ARRAY)
    plt.title('Queue in Lane')
    
    plt.subplot(3,1,2)
    plt.plot(QUEUE_DELAY_ENTRY_ARRAY_X, QUEUE_DELAY_ENTRY_ARRAY)
    plt.title('Queue at first place in roundabout')
    '''

    #plt.subplot(4, 1, i)
    plt.plot(QUEUE_DELAY_ENTRY_ARRAY_X, QUEUE_DELAY_TOTAL_ARRAY)
    plt.title('Total queue time')
plt.show()



