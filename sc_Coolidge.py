import json
import math
from random import randint

from clients.client_abstract_class import Player


class SubmarineCaptain(Player):
    def __init__(self, name):
        super(SubmarineCaptain, self).__init__(name=name, is_trench_manager=False)
        game_info = json.loads(self.client.receive_data())
        print('sub', game_info)
        self.m = game_info['m']
        self.L = game_info['L']
        self.position = game_info['pos']

    def play_game(self):
        response = {}
        forward = True
        scripted_bool = False
        move_list = []
        num = 0
        while True:
            forward, scripted_bool, num , move_list, move = self.your_algorithm(0 if not response else response['times_probed'],forward,scripted_bool,move_list,num)
            self.client.send_data(json.dumps({"move": move}))
            self.position += move
            response = json.loads(self.client.receive_data())
            if 'game_over' in response:
                print(f"The trench manager's final cost is: {response['trench_cost']}. " +
                      f"The safety condition {'was' if response['was_condition_achieved'] else 'was not'} satisfied.")
                exit(0)
            self.m -= 1

    def your_algorithm(self, times_probed,forward,scripted_bool,move_list,num):

        if times_probed > 0 and scripted_bool == False:
            scripted_bool = True
            wait = 10
            move_count = int(50 + wait * math.floor((50/(5+self.L))))
            move_list = []
            for i in range(move_count):
                if i%(self.L+wait) < self.L:
                    if forward:
                        move_list.append(1)
                    else:
                        move_list.append(-1)
                else:
                    move_list.append(0)
            num = 0

        if scripted_bool:
             #print move_list
             if num < len(move_list):
                 move = move_list[num]
                 num += 1
                 return forward, scripted_bool, num , move_list,move
             else:
                scripted_bool = False
                if forward:
                    forward = False
                    return forward, scripted_bool, num ,move_list, -1
                else:
                    forward = True
                    return forward, scripted_bool, num ,move_list, 1

        else:
            move_list = []
            if forward:
                return forward, scripted_bool, num , move_list, 1
            else:
                return forward, scripted_bool, num , move_list ,-1

        return forward, scripted_bool, num , move_list, 1
