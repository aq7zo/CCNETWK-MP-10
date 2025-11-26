Pokémon name: Sandshrew
Selected: Sandshrew (HP: 50, Type: ground/ice)

Starting battle with Sandshrew...
Waiting for opponent to select Pokémon...
Opponent chose Charmander

============================================================
  BATTLE START!
============================================================
Traceback (most recent call last):
  File "C:\Users\Admin\Documents\CCINFOM_ENZO\interactive_battle.py", line 417, in <module>
    main()
    ~~~~^^
  File "C:\Users\Admin\Documents\CCINFOM_ENZO\interactive_battle.py", line 408, in main
    run_interactive_joiner()
    ~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\Admin\Documents\CCINFOM_ENZO\interactive_battle.py", line 286, in run_interactive_joiner
    joiner.process_reliability()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\Admin\Documents\CCINFOM_ENZO\peer.py", line 295, in process_reliability
    self.send_message(message)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "C:\Users\Admin\Documents\CCINFOM_ENZO\peer.py", line 102, in send_message
    self.socket.sendto(data, target)
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
BlockingIOError: [WinError 10035] A non-blocking socket operation could not be completed immediately
PS C:\Users\Admin\Documents\CCINFOM_ENZO>