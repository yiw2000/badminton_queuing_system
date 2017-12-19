# badminton_queuing_system
Player queuing system for badminton club

Author: Yi Wang
Lauguage: Python

This software is used to control the queuing system in a badminton club (or any club to share courts among players).

The rules are:

- A player must check in to appear on the player list.
- Every time a player wants to join a court, he/she must login with a pin.
- A player can only join one court at any time.
- A court allows up to 4 players to play simultanously. If already have 4 players, the newly joined player must wait. A court can have up to 4 players waiting. 
- If all courts are full (with waiting queues are all of 4 players), no players can join any more.
- players currently occupying the court can play a period of time that was set by the club (i.e. a round). When a round is over, current players must give up the court to waiting players.
- If a round has 1/3 of time left, a new player can only join the waiting list, not the court directly. However, current players may accept the player to play already.
- If nobody is waiting. players can continue to play until other players joins this court.
- A player can withdraw from a court's waiting list; but cannot withdraw once start to play.
- After a round is over or withdraw from a waiting list, the player can now join a court again.
- courts that are closed or reserved are not open for play.
