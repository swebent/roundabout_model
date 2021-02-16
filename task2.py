import random

import simpy


class Roundabout(object):
    def __init__(self, env, size):
        self.env = env
        self.size = size
        self.space = simpy.Resource(env, capacity=size) # roundabout resource

        self.lock = simpy.Resource(env, capacity=1)     # mutex for resources below
        self.next_exit = ()                             # { 'dir' }
        self.occupying_cars = []                        # { 'exit_dir' : time of exit }

    def request_enter(self, car):

        if self.space.count >= self.size:               # if occupied
            with self.lock.request() as updater:
                yield updater
                n_exit = self.next_exit

            if n_exit == car.entry_lane:
                return True

        else:                                           # if space
            return True

        return False

    def enter(self, car):

        with self.lock.request() as updater:
            yield updater

            time = self.env.now + car.drive_time
            car.info = (car.exit_lane, time)

            self.occupying_cars.append(car.info)
            (curr_dir, curr_time) = self.next_exit

            if time < curr_time:
                self.next_exit = car.info
        return True

    def exit(self, car):
        i = 0
        temp = ()

        with self.lock.request() as updater:
            yield updater

            self.occupying_cars.remove(car.info)

            for (i_dir, i_time) in self.occupying_cars:
                if i == 0:
                    temp = (i_dir, i_time)
                if temp[1] > i_time:
                    temp = (i_dir, i_time)
                i += 1

            self.next_exit = temp


class Car:

    def __init__(self, env, roundabout, entry_lane, exit_lane, drive_time):
        self.env = env
        self.roundabout = roundabout
        self.entry_lane = entry_lane
        self.exit_lane = exit_lane
        self.drive_time = drive_time
        self.queue_time = 0
        self.car_info = ()

    def enter_roundabout(self, roundabout):

        while True:
            if roundabout.request_enter(self):
                with roundabout.space.request() as req:
                    yield req # should be 0 if roundabout has space

                    roundabout.enter(self)

                    yield self.env.timeout(self.drive_time)

                    roundabout.exit(self)


""""
this is the car generator. one will be created for each ingoing lane into the roundabout.
traffic is a function which returns the current traffic on the lane
""""
def source(env, traffic, lane_name, roundabout, lane_queue):
    """Source generates customers randomly"""
    for i in range(4):
        # generate drive time
        # generate exit lane

        c = Car(env, roundabout, lane_name, exit_lane, drive_time, lane_queue)
        env.process(c)

        # generate time between entering cars.
        time = traffic(env.now)
        yield env.timeout(time)

