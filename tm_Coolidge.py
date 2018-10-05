import json
import copy
import numpy as np
import math
import time
from random import randint, choice
import importlib

from clients.client_abstract_class import Player


class TrenchManager(Player):
    def __init__(self, name):
        super(TrenchManager, self).__init__(name=name, is_trench_manager=True)
        game_info = json.loads(self.client.receive_data())
        print('trench', game_info)
        self.d = game_info['d']
        self.y = game_info['y']
        self.r = game_info['r']
        self.m = game_info['m']
        self.L = game_info['L']
        self.p = game_info['p']

    def get_ec_mat(self,d,y,r,m,L,p):

        def intersection(lst1, lst2):
            return list(set(lst1) & set(lst2))

        def union(a, b):
            return list(set(a) | set(b))

        def diff(a,b):
            return list(set(a) - set(b))

        def ec(cost_mat,probe_pos,regions,i,j,KI,t,p,L,y,r,d):

            ec = 0
            prob_total = 0
            for reg in regions:

                new_KI = intersection(reg,KI)
                prob = len(new_KI)/float(len(KI))
                prob_total += prob


                if set(new_KI).isdisjoint(range(d,d+6)):
                    ec += prob * (y + cost_mat[(i-1)%100,(j+1)%100,t-1])
                else :
                    ec += prob * (r + cost_mat[(i-1)%100,(j+1)%100,t-1])

            ec += p *len(probe_pos)

            return ec

        def get_probe_space(probe_list):

            probe_space = []
            for i in range(len(probe_list)):
                for j in range((len(probe_list))-i):
                    probe_space.append([probe_list[i+k] for k in range(j+1)])

            probe_space.append([])
            return probe_space

        def get_probe_regions(probe_pos,L):

            if len(probe_pos) == 0:
                return [range(100)]
            if len(probe_pos) == 1:
                probe = probe_pos[0]
                inside = get_interval((probe-L)%100,(probe+L)%100)
                outside = diff(range(100),inside)
                return [outside,inside]
            else:
                first = probe_pos[0]
                last = probe_pos[-1]
                inside = get_interval((first-L)%100,(last+L)%100)
                outside = diff(range(100),inside)
                region = [outside]

                first_range = get_interval((first-L)%100,(first-1)%100)
                last_range = get_interval((last+1)%100,(last+L)%100)

                region += [first_range,last_range]
                region += [get_interval((probe_pos[i]+1)%100,(probe_pos[i+1]-1)%100) for i in range(len(probe_pos)-1)]
                region += [[probe] for probe in probe_pos]
                return region

        def get_interval(s,f):

            if s < f:
                return list(range(s,f+1))
            if s == f:
                return [s]
            if s > f:
                return list(range(s,100)) + list(range(0,f+1))

        num_list = list([4,4,3,2,1,3,2,4,2,1,1])
        num = num_list[self.L-2]
        probe_list = []
        probe_list += reversed([(d - i*L)%100 for i in range(int(num))])
        probe_list += [(d + (i+1)*L)%100 for i in range(int(num))]
        #probe_list = [(d-L)%100,d,(d+L)%100,(d+2*L)%100]
        probe_space = get_probe_space(probe_list)
        probe_regions = [get_probe_regions(probe_pos,L) for probe_pos in probe_space]

        cost_mat = np.empty(shape = (100,100,m+1))
        ec_mat = np.empty((100,100,m+1),dtype = np.ndarray)

        for i in range(1):
            for j in range(100):
                ec_mat[i,j,0] = [0 for probe_position_num in range(len(probe_list))]
                cost_mat[i,j,0] = 0

        max_time = 1
        for t in range(1,max_time+1):
            for i in range(100):
                for j in range(100):
                    ki = get_interval(i,j)
                    ec_vector = np.array([ec(cost_mat,probe_space[k],probe_regions[k],i,j,ki,t,p,L,y,r,d) for k in range(len(probe_space))])
                    index_min = ec_vector.argmin()
                    mec = ec_vector[index_min]
                    cost_mat[i,j,t] = mec
                    ec_mat[i,j,t] = np.array(ec_vector)

        return probe_space, ec_mat


    def play_game(self):
        probe_space, ec_mat = self.get_ec_mat(self.d,self.y,self.r,self.m,self.L,self.p)
        known_interval = list(range(100))
        while True:
            known_interval,probes_to_send = self.send_probes(known_interval,probe_space,ec_mat)
            self.client.send_data(json.dumps({"probes": probes_to_send}))
            response = json.loads(self.client.receive_data())
            known_interval, alert = self.choose_alert(probes_to_send, response['probe_results'],known_interval)
            self.client.send_data(json.dumps({"region": alert}))
            response = json.loads(self.client.receive_data())
            if 'game_over' in response:
                print(f"Your final cost is: {response['trench_cost']}. " +
                      f"The safety condition {'was' if response['was_condition_achieved'] else 'was not'} satisfied.")
                exit(0)
            self.m -= 1

    def send_probes(self,known_interval,probe_space,ec_mat):

        def split_interval(interval):

            if (interval[-1] - interval[0])%100 + 1 == len(interval):
                return [my_sort(interval)]
            else:
                i = 0
                while ((interval[i] + 1)%100 == (interval[i+1])%100):
                    i += 1
                return [my_sort(interval[0:i+1])] + split_interval(interval[i+1:])

        def my_sort(l):
            if len(l) == 0:
                return l
            l = sorted(l)
            if l[0] == 0:
                for i in range(len(l)-1):
                    if l[i+1] - l[i] != 1:
                        new_l = l[i+1:] + l[0:i+1]
                        return new_l
                return l
            else:
                return l

        def grow_interval(interval):
            interval_list = split_interval(interval)
            new_interval = []
            for i in interval_list:
                i = list(i)
                if len(i) == 100 or len(i) == 99 or len(i) == 98:
                    return list(range(100))
                else:
                    s = i[0]
                    f = i[-1]
                    i.append((s-1)%100)
                    i.append((f + 1)%100)
                    new_interval += i
            return my_sort(list(set(new_interval)))

        known_interval = grow_interval(known_interval)

        ki_split = split_interval(known_interval)
        ec_sum = np.zeros(len(probe_space))

        max_time = 1
        for i in ki_split:
            if self.m > max_time:
                ec_sum += (len(i)/float(len(known_interval))) * (ec_mat[i[0],i[-1],max_time])
            else:
                ec_sum += (len(i)/float(len(known_interval))) * (ec_mat[i[0],i[-1],self.m])

        probe_index = ec_sum.argmin()
        probes_placed = probe_space[probe_index]
        if probes_placed is None:
            probes_placed = []

        return known_interval, probes_placed

    def choose_alert(self, sent_probes,results,known_interval):

        def intersects_red(interval,d):
            red_interval = range(d,d+6)
            return not set(red_interval).isdisjoint(interval)

        def get_ki_with_results(known_interval,results,L,sent_probes):

            def intersection(lst1, lst2):
                return list(set(lst1) & set(lst2))

            def union(a, b):
                return list(set(a) | set(b))

            def get_interval(s,f):

                if s < f:
                    return list(range(s,f+1))
                if s == f:
                    return [s]
                if s > f:
                    return list(range(s,100)) + list(range(0,f+1))

            probe_range_list = []
            for probe in sent_probes:
                probe_range = get_interval((probe - L)%100, (probe + L)%100)
                probe_range_list.append(probe_range)

            responses = [i for i, x in enumerate(results) if x == True]
            if len(responses) == 0:
                not_known_interval = list(set(range(100)) - set(known_interval))

                for probe_range in probe_range_list:
                    not_known_interval = union(not_known_interval,probe_range)

                known_interval = list(set(range(100)) - set(not_known_interval))

            else:
                count = 0
                for r in results:
                    if r == True:
                        known_interval = intersection(known_interval,probe_range_list[count])
                    if r == False:
                        known_interval = list(set(known_interval) - set(probe_range_list[count]))
                    count += 1

            known_interval = np.sort(known_interval)
            if len(known_interval) == 0:
                known_interval = range(100)
            return known_interval

        known_interval = get_ki_with_results(known_interval,results,self.L,sent_probes)
        if not intersects_red(known_interval,self.d):
            alert = 'yellow'
        else:
            alert = 'red'
        return known_interval, alert
