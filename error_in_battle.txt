File "c:\Users\davej\Downloads\UP_CSNETWK-20251107T114549Z-1-001\UP_CSNETWK\interactive_battle.py", line 417, in <module>
    main()
    ~~~~^^
  File "c:\Users\davej\Downloads\UP_CSNETWK-20251107T114549Z-1-001\UP_CSNETWK\interactive_battle.py", line 406, in main
    run_interactive_host()
    ~~~~~~~~~~~~~~~~~~~~^^
  File "c:\Users\davej\Downloads\UP_CSNETWK-20251107T114549Z-1-001\UP_CSNETWK\interactive_battle.py", line 151, in run_interactive_host
    host.process_reliability()
    ~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "c:\Users\davej\Downloads\UP_CSNETWK-20251107T114549Z-1-001\UP_CSNETWK\peer.py", line 295, in process_reliability
    self.send_message(message)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "c:\Users\davej\Downloads\UP_CSNETWK-20251107T114549Z-1-001\UP_CSNETWK\peer.py", line 102, in send_message
    self.socket.sendto(data, target)
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
BlockingIOError: [WinError 10035] A non-blocking socket operation could not be completed immediately