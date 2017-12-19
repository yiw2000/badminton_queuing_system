# -*- coding: utf-8 -*-

# copyright 2017 Yi Wang
# don't distribute without author's explicit authorization

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as mb
import tkinter.simpledialog as dlg
import tkinter.scrolledtext as st

import traceback as tb
import sys
import queue
from smart_combobox import smart_combobox
import queue


DEBUG = 1
COURTS_PER_ROW = 6

instruction = """\
To Join a court:
-----------------
1. Choose your login name from the "players" pull down list. 
    -    The login name is your first name concatenated with your last name. 
    -    The first name maybe truncated; 
    -    If there are same names, the last 2 digits of your ID maybe concatenated. 
    -    You can type in first letters for fast lookup.
2. A login dialog will pop up. Input your pin (the last 4 digits of your ID) and click OK.
3. A confirmation dialog will pop up if login successfully; otherwise, an error dialog will show. 
    -    You can try up to 3 times. Contact front desk if you forgot your pin.
4. Choose a court by clicking the court button. 
    -    A court can have up to 4 players playing, and up to 4 players waiting. 
    -    You will be placed on the court if less than 4 players are playing; 
    -    If less than 1/3 of time has left for the round, you will be added to the waiting queue; 
    -    If 4 players are already playing, you will be added to the waiting queue.
5. You can join one and only one court.
6. Your time will become red when it is less than 1 minute.
7. Please give up the court when your time is up.

To withdraw from waiting list:
------------------------------
1. Once joined a court, you can withdraw only if you are in the waiting queue. 
    -    Select your login name from the "waiting players" pull down list and login.    
""".strip()

banner_messages = """\
    -    Training available for juniors of all ages. 
    -    Winter session is now open for registration, act soon!    
    -    Keep your belonging close to you. Keep your unused equipment in your bag.  
    -    Be courteous to your fellow players, watch for people passing by.    
    -    You can ADVERTISE HERE for a fraction of cost! Contact the front desk for details.    
    -    Please share your invaluable feedback. Talk to our staff and/or leave your comment at the front desk!

    REMEMBER, YOU CAN ALWAYS RELY ON THE FRIENDLY CBA STAFF FOR ANY ASSISTANCE!    
"""

play_font           = 'Monaco 10'
state_font          = 'Arial 16 bold'
message_font        = 'Arial 10 italic'
timer_font          = 'Monaco 16 bold'

open_color          = 'pale green'
play_color          = 'light yellow'
full_color          = 'pale violet red'
timer_normal_color  = 'green'

class two_entry_dialog(dlg.Dialog):
    def __init__(self, master, title):
        dlg.Dialog.__init__(self, master, title)
        
    def body(self, master = None):
        tk.Label(master, text = 'courts').grid(row = 0)
        tk.Label(master, text = 'period').grid(row = 1)

        self.e1 = tk.Entry(master)
        self.e2 = tk.Entry(master)

        self.e1.grid(row = 0, column = 1, padx = 10)
        self.e2.grid(row = 1, column = 1, padx = 10)
        return self.e1 # initial focus

    def apply(self):
        first = self.e1.get()
        second = self.e2.get()
        self.result = first, second 
        
class court_widget(object):
    def __init__(self, court, timer, button):
        self.court = court
        self.button = button
        self.timer = timer
        self.timer_display = timer.get_timer_display()       
        
    def start(self):
        self.timer.start()
        
    def reset_to_open(self):
        self.court.reset()
        self.timer.reset()
        self.button['bg'] = open_color
        self.button['font'] = play_font
        self.court['text'] = 'OPEN'
        self.timer_display['fg'] = timer_normal_color  
        
    def reset(self):
        self.court.reset()
        self.timer.reset()  
    
    def set_button_text(self, additional_msg = ''):
        if self.court.get_state() != 'ACTIVE' or self.court.is_empty():
            self.button['font'] = state_font
        else :
            self.button['font'] = play_font
            
        msg = str(self.court)
        if additional_msg != '':
            msg += '\n' + additional_msg
        self.button['text'] = msg
        
    def set_button_bg(self):
        if self.court.is_full() :
            self.button['bg'] = full_color
        elif self.court.is_playing() :
            self.button['bg'] = play_color
        else :
            self.button['bg'] = open_color
    
    def set_interval(self, interval):
        self.timer.set_interval(interval)
    
    def refresh(self):
        self.set_button_text()
        self.set_button_bg()
              
    def update(self, state = 'normal', timer_text = '', additional_msg = ''):
        self.set_button_text(additional_msg)
        self.set_button_bg()
        self.button['state'] = state
        if timer_text != '':
            self.timer_display['text'] = timer_text
         
    def reserve(self, additional_msg):   
        self.reset()
        self.court.set_state('RESERVED')
        self.update('disabled', '0:0:0', additional_msg)
    
    def close(self, additional_msg):   
        self.reset()
        self.court.set_state('CLOSED')
        self.update('disabled', '0:0:0', additional_msg)
        
    def open(self):
        self.court.set_state('ACTIVE')
        self.update('normal', queue.conv_time(self.timer.get_interval()))
 
###############
# Main app
#############                           
class Application(tk.Frame):
    def __init__(self, master):
        tk.Frame.__init__(self, master)
        self.grid()
        self.timer_displays = []
        self.courts = []
        self.cur_player = ''
        if DEBUG == 1 :
            self.interval = 20 # in seconds
        else :
            self.interval = 1200 # 20 minutes
        self.gym = queue.gym()
        self.num_courts = self.gym.get_num_courts()
        self.hide_instruction = True
        self.is_admin = False
        
        # fonts and colors
        self.create_widgets()
        self.toggle_instruction()
        self.hide_admin()

        self.init_all_courts()
                    
    def create_widgets(self):
        # 2 panels inside. 1 for courts, 1 for player
        
        self.pw = tk.PanedWindow(self, orient = "vertical", 
                                 borderwidth = 1, relief = 'solid', sashwidth = 1)
        self.pw.pack(side = tk.TOP, fill = tk.BOTH, expand = 1)
        
        self.title_pane = tk.Frame(self.pw)
        self.court_pane = tk.Frame(self.pw)
        self.top_pane = tk.PanedWindow(self.pw, orient = 'horizontal')
        self.admin_pane = tk.Frame(self.pw) # admin pane adds on demand
        self.pw.add(self.title_pane, pady = 10, padx = 20)
        self.pw.add(self.top_pane, pady = 10, padx = 10)
        self.pw.add(self.court_pane, pady = 0, padx = 10)
        self.player_pane = tk.Frame(self.top_pane, padx = 10)
        self.message_pane = tk.Frame(self.top_pane, padx = 40)
        self.top_pane.add(self.player_pane)
        self.top_pane.add(self.message_pane)
        
        # title pane
        self.title_label = tk.Label(self.title_pane, text = "CBA player queuing system",
                                    font = 'Monaco 16 bold', fg = 'dark green')
        self.title_label.grid(row = 0, column = 0, sticky= tk.N)
        # court pane
        self.court_buttons = []
        for i in range(self.num_courts) :
            r = int(i / COURTS_PER_ROW) * 3
            c = i % COURTS_PER_ROW
            label = tk.Label(self.court_pane, text = "Court {0}".format(i + 1))
            label.grid(row = r, column = c)
            
            button_width_in_pixel = 252
            button_height_in_pixel = 145
            b_frame = tk.Frame(self.court_pane, width = button_width_in_pixel, height = button_height_in_pixel)
            b_frame.rowconfigure(0, minsize = button_height_in_pixel, pad = 0)
            b_frame.columnconfigure(0, minsize = button_width_in_pixel, pad = 0)
            b_frame.grid(row = r + 1, column = c)
            parent = b_frame
            button = tk.Button(parent, text = 'OPEN', bg = open_color,
                               command = lambda court_id = i : self.sel_court(court_id), 
                               #width = 38, height = 14, 
                               justify = tk.LEFT, font = state_font)
            button.grid(row = 0, column = 0, sticky = 'EWNS')
            self.court_buttons.append(button)
            b_frame.grid_propagate(False)

            times = tk.Label(self.court_pane, fg = timer_normal_color, 
                             text = queue.conv_time(self.interval),
                             font = timer_font)
            times.grid(row = r + 2, column = c)
            self.timer_displays.append(times)
             
        # player pane
        tk.Label(self.player_pane, text = "waiting players:").grid(row = 1, column = 0, 
                                                                   padx = 10, sticky= tk.N)
        self.waiting_player_list = smart_combobox(self.player_pane, height = 40)
        self.set_waiting_player_list()
        self.waiting_player_list.set('')
        self.waiting_player_list.bind("<<ComboboxSelected>>", self.waiting_player_selected)
        self.waiting_player_list.bind("<Return>", self.waiting_player_selected)
        self.waiting_player_list.grid(row = 1, column = 1, sticky = tk.N, padx = 10)
        
        tk.Label(self.player_pane, text = "players:").grid(row = 0, column = 0, padx = 10)
        self.player_list = smart_combobox(self.player_pane, height = 40)
        self.set_player_list()
        self.player_list.set('')
        self.player_list.bind("<<ComboboxSelected>>", self.player_selected)
        self.player_list.bind("<Return>", self.player_selected)
        self.player_list.grid(row = 0, column = 1, sticky = tk.W, padx = 10)
        
        self.refresh_player_button = tk.Button(self.player_pane, text = 'Refresh', 
                                               command = self.refresh_players)
        self.refresh_player_button.grid(row = 0, column = 2)
        
        self.inst_button = tk.Button(self.player_pane, text = 'Show Instruction', 
                                     command = self.toggle_instruction)
        self.inst_button.grid(row = 0, column = 3)       
        self.instruction_msg = st.ScrolledText(self.message_pane, font = message_font, 
                                               fg = 'blue', bd = 2, relief = 'ridge',
                                               width = 140, height = 8)
        self.instruction_msg.insert(tk.END, instruction)
        self.instruction_msg.grid(row = 0, column = 0)
        

        # admin pane
        self.admin_close_court_button = tk.Button(self.admin_pane, text = 'Close Courts',
                                                  command = self.admin_close_courts)
        self.admin_reserve_court_button = tk.Button(self.admin_pane, text = 'Reserve Courts',
                                                    command = self.admin_reserve_courts)
        self.admin_set_interval_button = tk.Button(self.admin_pane, text = 'Set Interval',
                                                   command = self.admin_set_interval)
        self.admin_open_button = tk.Button(self.admin_pane, text = 'Open All',
                                           command = self.admin_open_all)
        self.admin_remove_player_button = tk.Button(self.admin_pane, text = 'Remove Player',
                                                    command = self.admin_remove_player)
        self.admin_open_court_button = tk.Button(self.admin_pane, text = 'Open Courts',
                                                    command = self.admin_open_courts)
        
        self.admin_done_button = tk.Button(self.admin_pane, text = 'Done', command = self.admin_done)
        self.admin_exit_button = tk.Button(self.admin_pane, text = 'Exit App', command = exit)
        
        self.admin_close_court_button.grid(row = 0, column = 0, padx = 10, sticky = tk.W)
        self.admin_reserve_court_button.grid(row = 0, column = 1, padx = 10, sticky = tk.W)
        self.admin_set_interval_button.grid(row = 0, column = 2,  padx = 10, sticky = tk.W)
        self.admin_open_button.grid(row = 0, column = 3, padx = 10, sticky = tk.W)
        self.admin_remove_player_button.grid(row = 0, column = 4, padx = 10, sticky = tk.W)
        self.admin_open_court_button.grid(row = 0, column = 5, padx = 10, sticky = tk.W)
        self.admin_done_button.grid(row = 0, column = 10, padx = 10, sticky = tk.W)
        self.admin_exit_button.grid(row = 0, column = 11, padx = 10, sticky = tk.W)
    
    def toggle_instruction(self):
        self.instruction_msg['state'] = 'normal'
        if self.hide_instruction is False :
            self.instruction_msg.delete(1.0, tk.END)
            self.instruction_msg.insert(tk.END, instruction)
            self.instruction_msg['fg'] = 'blue'
            self.inst_button['text'] = 'Hide Instruction'
            self.hide_instruction = True
        else :
            self.instruction_msg.delete(1.0, tk.END)
            self.instruction_msg.insert(tk.END, banner_messages)
            self.instruction_msg['fg'] = 'purple'
            self.inst_button['text'] = 'Show Instruction'
            self.hide_instruction = False
        self.instruction_msg['state'] = 'disabled'        
             
    def waiting_player_selected(self, event):
        player = self.waiting_player_list.get()
        if DEBUG != 1 and not self.login(player) :
            return
        if mb.askyesno('withdraw', 'Withdraw from waiting list?') :
            self.remove_waiting_player(player)
            
    def set_waiting_player_list(self):
        waiting_players = self.gym.get_waiting_players()
        if not waiting_players:
            self.waiting_player_list.set('')
            self.waiting_player_list.set_values('')
        else :
            self.waiting_player_list.set_values(tuple(waiting_players))
            self.waiting_player_list.set('')
        
    def player_selected(self, event):
        player = self.player_list.get()
        if player == 'CBA_ADMIN':
            if self.login(player) :
                self.show_admin()
                self.player_list['state'] = 'disabled'
            return    
        if DEBUG:
            return
        if not self.login(player) :
            return
        mb.showinfo('login', 'login successful, please select court to join!')
        self.cur_player = player
   
    def login(self, player):
        i = 3
        while i >= 0:
            pin = dlg.askstring("pin", "enter your pin", show = "*")
            if not pin:
                self.reset_cur_player()
                self.waiting_player_list.set('')
                return False
            i = i - 1
            if not self.gym.check_player(player, pin):
                if i > 0 :
                    if not mb.askretrycancel('wrong pin', 'wrong pin, retry?'):
                        self.reset_cur_player()
                        self.waiting_player_list.set('')
                        return False
                else :
                    mb.showerror("wrong pin", "3 attempts failed. Please talk to front desk.")
                    self.reset_cur_player()
                    self.waiting_player_list.set('')
                    return False
            else :
                return True
        return False     
       
    def reset_cur_player(self):
        self.cur_player = ''
        self.player_list.set('')
        
    def refresh_players(self):
        self.gym.read_players()
        self.set_player_list()
    
    def remove_waiting_player(self, player):
        if player is None or player == '':
            return
        num = self.gym.remove_player_from_wait(player)
        if num != -1 :
            self.courts[num].refresh()
            self.set_player_list()
            mb.showinfo('Remove Waiting', 'Removed player {} from court {}'.format(player, num + 1))
        else :
            mb.showerror('Remove Waiting', 'Cannot find player {} or player is playing'.format(player))

    def admin_done(self):
        self.player_list['state'] = 'normal'
        self.set_player_list()
        self.hide_admin()
              
    def admin_open_all(self):
        for i in range(self.num_courts):
            self.open_court(i)
            
    def admin_reserve_courts(self):
        d = two_entry_dialog(self, 'Reserve courts')     
        if d.result is None:
            return
        courts = d.result[0].split(' ')
        period = d.result[1].upper()
        for c in courts:
            try:
                n = int(c) - 1
                if n >= 0 and n < self.num_courts:
                    self.reserve_court(n, period)
            except:
                pass
    
    def admin_open_courts(self):
        open_courts = dlg.askstring('Open Courts', 'courts to open')
        if not open_courts:
            return
        for r in open_courts:
            try:
                n = int(r) - 1
                if n >= 0 and n < self.num_courts:
                    self.open_court(n)
            except:
                pass
            
    def admin_close_courts(self):
        d = two_entry_dialog(self, 'Close courts')     
        if d.result is None:
            return
        courts = d.result[0].split(' ')
        period = d.result[1].upper()

        for c in courts:
            try:
                n = int(c) - 1
                if n >= 0 and n < self.num_courts:
                    self.close_court(n, period)
            except:
                pass
            
    def admin_set_interval(self):
        interval = dlg.askinteger("Set Interval", "interval in seconds [0, 3600]")
        if not interval:
            return
        if interval < 0 or interval > 3600 :
            mb.showerror("interval should be in [0, 3600]")
            return
        self.interval = interval
        for c in self.courts:
            c.set_interval(interval)
        for i in range(self.num_courts):
            self.courts[i].set_interval(interval)
            if self.court_buttons[i]['state'] == 'normal':
                if self.gym.get_court(i).is_empty():
                    self.timer_displays[i]['text'] = queue.conv_time(self.interval)

    def admin_remove_player(self):
        player = dlg.askstring("Remove player", "player to remove")
        if player is None:
            return
        num = self.gym.remove_player_from_court(player)
        if num != -1 :
            self.courts[num].refresh()
            self.set_player_list()
                                
    def show_admin(self):
        self.is_admin = True
        self.pw.add(self.admin_pane, pady = 10)
        
    def hide_admin(self):
        self.is_admin = False
        self.pw.remove(self.admin_pane)      
    
    def init_all_courts(self):
        for i in range(self.num_courts):
            court = self.gym.get_court(i)
            timer = queue.count_down_timer(self.interval, court, 
                                           self.timer_displays[i], self.timer_callback)
            self.courts.append(court_widget(court, timer, self.court_buttons[i]))
    
    def start_court(self, num):
        self.courts[num].start()
        
    def timer_callback(self, num):
        self.courts[num].update(timer_text = queue.conv_time(self.interval))
        self.set_player_list()
                
    def set_player_list(self):
        free_players = self.gym.get_free_players()
        if not free_players:
            self.player_list.set('')
            self.player_list.set_values('')
            self.cur_player = ''
        else :
            free_players.sort()
            self.player_list.set_values(tuple(free_players))
            self.player_list.set('')
        
        self.set_waiting_player_list()
         
    def sel_court(self, num):
        if self.is_admin:
            return
        player = self.player_list.get().strip()
        if player not in self.player_list['value'] or player is None:
            mb.showerror('invalid player', 'Please select a valid player name in the players pull down.')
            return
        
        msg = "'{}' to join court {}?\n".format(player, num + 1)
        if not mb.askokcancel('Join court', msg):
            return
        
        if self.gym.add_to_court(player, num) :
            self.update_court(num)
            self.start_court(num)
        else:
            mb.showerror('Cannot add', 'Court {} is not open or full'.format(num + 1))
            
        # update widgets
        self.set_player_list()
        self.reset_cur_player()
    
    def update_court(self, num):
        self.courts[num].refresh()
          
    def reserve_court(self, num, period):
        court = self.gym.get_court(num)
        if court.is_playing() :
            if not mb.askyesno('reserve court', 'court {} is playing, still reserve it?'.format(num + 1)) :
                return    
        self.courts[num].reserve(period)
    
    def close_court(self, num, period):
        court = self.gym.get_court(num)
        if court.is_playing() :
            if not mb.askyesno('close court', 'court {} is playing, still close it?'.format(num + 1)) :
                return      
        self.courts[num].close(period)
        
    def open_court(self, num):
        self.courts[num].open()
        
def exit():
    if mb.askokcancel('Exit', 'Exit the application?') :
        sys.exit()

def do_nothing():
    if DEBUG :
        exit()
    pass
         
main_window = tk.Tk()
main_window.title("CBA Court Queuing System")
main_window.resizable(0, 0)
main_window.overrideredirect(True)
main_window.protocol('WM_DELETE_WINDOW', do_nothing)
main_window.attributes('-toolwindow', 1)

if not DEBUG :
    main_window.geometry("{}x{}".format(main_window.winfo_screenwidth() - 40, 
                                        main_window.winfo_screenheight() - 40))
#main_window.state('zoomed')
#main_window.geometry("800x600")

app = Application(main_window)
app.grid()

# event loop
main_window.mainloop()