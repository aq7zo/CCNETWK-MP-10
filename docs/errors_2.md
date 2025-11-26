## Host
```
18. Pidgeot
19. Rattata
20. Raticate
21. Spearow
22. Fearow
23. Ekans
24. Arbok
25. Pikachu
26. Raichu
27. Sandshrew
28. Sandslash
29. Nidoran♀
30. Nidorina

... and 771 more
Pokémon name: Charmander
Selected: Charmander (HP: 39, Type: fire/None)

Starting battle with Charmander...
Waiting for opponent to select Pokémon...
Opponent chose Pikachu

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
  File "C:\Users\Admin\Documents\CCINFOM_ENZO\interactive_battle.py", line 284, in run_interactive_joiner
    joiner.handle_message(msg, addr)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "C:\Users\Admin\Documents\CCINFOM_ENZO\peer.py", line 221, in handle_message
    self._handle_battle_message(message, address)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
  File "C:\Users\Admin\Documents\CCINFOM_ENZO\peer.py", line 755, in _handle_battle_message
    self._handle_attack_announce(message)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "C:\Users\Admin\Documents\CCINFOM_ENZO\peer.py", line 802, in _handle_attack_announce
    self.my_pokemon.pokemon,
    ^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'Pokemon' object has no attribute 'pokemon'
PS C:\Users\Admin\Documents\CCINFOM_ENZO>
```

## Joiner
```
12. Butterfree
13. Weedle
14. Kakuna
15. Beedrill
16. Pidgey
17. Pidgeotto
18. Pidgeot
19. Rattata
20. Raticate
21. Spearow
22. Fearow
23. Ekans
24. Arbok
25. Pikachu
26. Raichu
27. Sandshrew
28. Sandslash
29. Nidoran♀
30. Nidorina

... and 771 more
Pokémon name: Pikachu
Selected: Pikachu (HP: 35, Type: electric/None)

Starting battle with Pikachu...
Waiting for opponent to select Pokémon...
Opponent chose Charmander

============================================================
  BATTLE START!
============================================================

Pikachu: 35/35 HP vs Charmander: 39/39 HP

Your turn! Select a move:
1. Quick Attack (Electric moves)
2. Strong Attack (Fire moves)
3. Special Attack (Water moves)
4. Custom move name
Enter choice (1-4): 1
1. Thunder Shock (Power: 40, Type: electric)
2. Thunderbolt (Power: 90, Type: electric)
Select move (1-3): 1
Used Thunder Shock!
Traceback (most recent call last):
  File "C:\Users\Admin\Documents\CCINFOM_ENZO\interactive_battle.py", line 417, in <module>
    main()
    ~~~~^^
  File "C:\Users\Admin\Documents\CCINFOM_ENZO\interactive_battle.py", line 406, in main
    run_interactive_host()
    ~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\Admin\Documents\CCINFOM_ENZO\interactive_battle.py", line 191, in run_interactive_host
    host.battle_state.mark_my_turn_taken()
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'BattleStateMachine' object has no attribute 'mark_my_turn_taken'
PS C:\Users\Admin\Documents\CCINFOM_ENZO>
```