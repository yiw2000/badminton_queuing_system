# -*- coding: utf-8 -*-

# copyright 2017 Yi Wang
# don't distribute without author's explicit authorization

import collections
import sys
import threading
import time
import itertools as it

import query

ACTIVE      = 'ACTIVE'
RESERVED    = 'RESERVED'
CLOSED      = 'CLOSED'
OPEN        = 'OPEN'
OTHER       = 'OTHER'

WAIT_LIMIT  = 4
NAME_LENTGH = 16

DEBUG = 1

queued_players = []

def free_player(player):
    lock = threading.Lock()
    lock.acquire()
    try:
        queued_players.remove(player)
    except ValueError:
        pass
    lock.release()

def free_players(players):
    lock = threading.Lock()
    lock.acquire()
    try:
        for x in players :
            queued_players.remove(x)
    except ValueError:
        pass
    lock.release()

def conv_time(seconds):
    hour = int(seconds / 3600)
    minute = int(seconds / 60)
    second = seconds % 60
    return str(hour) + ':' + str(minute) + ':' + str(second)
    
class count_down_timer(object):
    def __init__(self, interval, court, time_display, call_back):
        self.interval = interval
        self.start_time = 0
        self.started = False
        self.time_display = time_display
        self.court = court
        self.timer = None
        self.printer = None
        self.filler = None
        self.call_back = call_back
    
    def get_timer_display(self):
        return self.time_display
    
    def get_interval(self):
        return self.interval
        
    def set_interval(self, interval):
        self.interval = interval
        
    def round_end(self):
        self.court.round_end()
        self.time_display['fg'] = 'green'
        self.call_back(self.court.get_id())
        self.reset()
        if not self.court.is_empty() :
            self.start()
        
    def start(self):
        if self.started is True:
            return
        self.started = True
        self.start_time = time.time()
        self.printer = threading.Timer(1, self.report_time)
        self.printer.daemon = True
        self.printer.start()
        self.filler = threading.Timer(int(self.interval * 0.60), self.set_court_full)
        self.filler.daemon = True
        self.filler.start()
        self.timer = threading.Timer(self.interval, self.round_end)
        self.timer.daemon = True
        self.timer.start()
        self.court.start()
            
    def reset(self):
        if self.timer:
            self.timer.cancel()
        if self.printer:
            self.printer.cancel()
        if self.filler:
            self.filler.cancel()
        self.start_time = 0
        self.started = False
        self.time_display['fg'] = 'green'
        #self.time_display['text'] = conv_time(self.interval)
    
    def report_time(self):
        remaining = self.interval - int(time.time() - self.start_time)
        if remaining < 60 :
            self.time_display['fg'] = 'red'
        else : 
            self.time_display['fg'] = 'green'
        self.time_display['text'] = conv_time(remaining)
        if remaining > 0 :
            self.printer = threading.Timer(1, self.report_time)
            self.printer.daemon = True
            self.printer.start()
    
    def set_court_full(self):
        self.court.set_full()

class court(object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        self.state = ACTIVE
        self.cur_players = []
        self.wait_players = []
        self.started = False
        self.full = False

    def is_empty(self):
        if self.cur_players:
            return False
        return True
    
    def get_id(self):
        return self.id
    
    def get_waiting_players(self):
        return self.wait_players
    
    def is_full(self):
        if self.state != ACTIVE:
            return True
        if len(self.wait_players) is WAIT_LIMIT :
            return True
        return False
    
    def set_full(self):
        if self.started: 
            self.full = True
        
    def is_playing(self):
        if len(self.cur_players) > 0:
            return True
        return False
    
    def add(self, player):
        if self.state != ACTIVE:
            return False
        if len(self.cur_players) >= 4 or self.full:
            if len(self.wait_players) >= WAIT_LIMIT :
                return False
            else :
                self.wait_players.append(player)
        else :
            self.cur_players.append(player)
        return True
    
    def remove(self, player):
        if player in self.wait_players:
            self.wait_players.remove(player)
            free_player(player)
        elif player in self.cur_players:
            self.cur_players.remove(player)
            free_player(player)
        
    def is_player_waiting(self, player):
        if player in self.wait_players:
            return True
        return False
    
    def is_player_on_court(self, player):
        if player in self.wait_players:
            return True
        if player in self.cur_players:
            return True
        return False
   
    def start(self, force = False):
        if self.state != ACTIVE :
            return
        if self.started is True and force is False :
            return
        self.started = True
    
    def round_end(self):
        self.started = False
        self.full = False
        players = self.cur_players
        if players :
            free_players(players)
            self.cur_players.clear()
            self.cur_players.extend(self.wait_players)
            self.wait_players.clear()
          
    def reset(self):
        players = self.cur_players
        players.extend(self.wait_players)
        self.cur_players.clear()
        self.wait_players.clear()
        self.full = False
        self.set_state(ACTIVE)      
        if players:
            free_players(players)
    
    def set_state(self, state):
        self.state = state
    
    def get_state(self):
        return self.state       
        
    def __str__(self):
        if self.state is ACTIVE :
            text = ''
            if self.cur_players and self.wait_players:
                text += '{} {}\n\n'.format('Current'.ljust(NAME_LENTGH, ' '), 'Wait:')
                for i, j in it.zip_longest(self.cur_players, self.wait_players, fillvalue = ''):
                    text += '{} {}\n'.format(i.ljust(NAME_LENTGH, ' '), j)
            elif self.cur_players:
                text = 'Current:\n\n' + '\n'.join(self.cur_players)
            else :
                text = 'OPEN'
            return text
        else :
            return("{}".format(self.get_state()))
    


class gym(object):
    def __init__(self):
        self.name = 'CBA'
        self.courts = []
        self.num_courts = 18
        self.players = dict()
        
        for i in range(self.num_courts):
            name = 'court ' + str(i + 1)
            self.courts.append(court(name, i))
        
        self.read_players()
    
    def set_num_courts(self, num_courts):
        self.num_courts = num_courts
    
    def read_players(self):
        if DEBUG == 1:
            self.read_local_db()
        else :
            self.players = query.read_clients()
            self.write_local_db()
        # adding admin
        self.add_player('CBA_ADMIN', 100000000, '1111')
            
    def check_player(self, name, pin):
        player = self.players[name]
        if not player:
            return False
        if player.get_pin() != pin :
            return False
        return True
        
    def get_num_courts(self):
        return self.num_courts
    
    def get_court(self, id):
        return self.courts[id]
    
    def get_players(self):
        return self.players.keys()
    
    def get_waiting_players(self):
        players = list()
        for i in range(self.num_courts):
            court = self.courts[i]
            players.extend(court.get_waiting_players())
        return players
            
    def get_free_players(self):
        names = self.get_players()
        return [x for x in names if x not in queued_players]
    
    def add_player(self, name, pid, pin):
        self.players[name] = query.player(name, pid, pin)

    def remove_player_from_court(self, player):
        for i in range(self.num_courts):
            court = self.courts[i]
            if court.is_player_on_court(player) :
                court.remove(player)
                return i
        return -1
            
    def remove_player_from_wait(self, player):
        for i in range(self.num_courts):
            court = self.courts[i]
            if court.is_player_waiting(player) :
                court.remove(player)
                return i
        return -1
    
    def add_to_court(self, player, court_id):
        if player in queued_players :
            return False
        court = self.courts[court_id]
        if court.add(player):
            queued_players.append(player)
            return True
        return False
        
    def reserve_court(self, court_id):
        self.courts[court_id].set_state(RESERVED)
    
    def reset_court(self, court_id):
        self.courts[court_id].set_state(ACTIVE)
    
    def close_court(self, court_id):
        self.courts[court_id].set_state(CLOSED)
        
    def write_local_db(self):
        with open('CBA_player_info', 'w', encoding = 'utf8') as f: 
            for v in self.players.values() :
                f.write('{}\n'.format(v))
    
    def read_local_db(self):
        with open('CBA_player_info', 'r', encoding = 'utf8') as f: 
            for line in f:
                p = line.strip('\n').split(' ')
                self.add_player(p[0], p[1], p[2])
            

#g = gym()
#g.start()