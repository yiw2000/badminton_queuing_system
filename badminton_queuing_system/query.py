# -*- coding: utf-8 -*-

# copyright 2017 Yi Wang
# don't distribute without author's explicit authorization

# MindBody API

from suds.client import Client 
import ClientRequest

class player(object):
    def __init__(self, name, pid, pin, phone = '5555555555'):
        self.name = name
        self.id = pid
        self.pin = pin
        self.phone = phone

    def get_pin(self):
        return self.pin
    
    def get_name(self):
        return self.name
    
    def get_phone(self):
        return self.phone
    
    def __str__(self):
        return("{} {} {}".format(self.name, self.id, self.pin))
    
def read_clients():
    services = ClientRequest.ClientServiceMethods()
    
    #get all clients
    result = services.GetAllClients()
    
    client_dict = Client.dict(result)
    clients = client_dict['Clients'].Client
    player_names = set()
    players = dict()
    
    num_clients = len(clients)
    for i in range(num_clients) :
        client = clients[i]
        first_name = client.FirstName.lower()
        last_name = client.LastName.lower()
        id = client.UniqueID
        
        try :
            pin = str(id)[-4:]
            name = first_name + last_name
            if len(name) > 16:
                if len(last_name) > 16:
                    name = last_name[0:15]
            else:
                temp = 16 - len(last_name)
                name = first_name[0:temp] + last_name
            
            if name in player_names:
                name += pin[-2:]
                
            player_names.add(name)
        except ValueError:
            pass
        finally:
            players[name] = player(name, id, pin)            
        
    return players
