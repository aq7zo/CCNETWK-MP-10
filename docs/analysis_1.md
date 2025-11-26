Findings

  - Reliability spec requires a sequence_number on every non-ACK message (docs/Copy of RFC PokeProtocol.md:247-249), but
    HandshakeRequest, HandshakeResponse, SpectatorRequest, and BattleSetup omit the field entirely, so BasePeer never
    ACKs them because it only acknowledges objects with a sequence_number attribute (messages.py:122-220, peer.py:142-
    150). This breaks the RFC-mandated retry/ack guarantees for the entire setup phase.
  - The RFC defines three communication modes, including Broadcast discovery (docs/Copy of RFC PokeProtocol.md:26-
    35) and expects peers to advertise/game-select via the communication_mode field in BATTLE_SETUP (docs/Copy of RFC
    PokeProtocol.md:83-89). The implementation hardcodes "P2P" when sending setup messages and never branches on that
    value anywhere else (peer.py:346-374, peer.py:553-580), nor does it configure or send any broadcast traffic, leaving
    the broadcast workflow completely unimplemented.
  - Spectator support described in the RFC (docs/Copy of RFC PokeProtocol.md:26-35, 68-78) is missing. The host never
    handles SPECTATOR_REQUEST, and there is no code to keep observers synced; moreover SpectatorPeer is an empty
    subclass (peer.py:262-277, peer.py:765-767). As written, spectators cannot join, receive battle updates, or send
    chat as mandated.
  - Sticker-capable chat is required (docs/Copy of RFC PokeProtocol.md:211-236), but _handle_chat_message explicitly
    ignores stickers and send_chat_message only emits plain text (peer.py:157-167, peer.py:179-194). There is no API to
    send Base64 sticker data, no validation of the 320×320 sticker constraints, and no UI callback for receiving them.
  - BATTLE_SETUP is supposed to include the full Pokémon object so a peer can battle without out-of-band data (docs/
    Copy of RFC PokeProtocol.md:83-89), yet the serializer only sends communication_mode, pokemon_name, and stat_boosts
    (messages.py:199-211). Remote peers must already possess matching datasets, which contradicts the spec’s serialized-
    data contract.
  - The RFC’s revision introduces limited-use special attack/defense boosts defined during setup (docs/Copy of
    RFC PokeProtocol.md:8), but those counts are merely stored on BattlePokemon and never consumed or applied to
    calculations (battle_state.py:33-80, damage_calculator.py:65-90). No message lets a player spend a boost, and the
    damage math always uses the base stats, so the advertised mechanic doesn’t exist.

  Next steps (suggested):

  1. Extend the message schema so every protocol message (including handshake/setup/spectator) carries a
     sequence_number, and update the reliability layer/handlers accordingly.
  2. Design and wire the broadcast and spectator workflows: add socket broadcast support, honor the communication_mode,
     and implement real spectator join/receive loops plus host-side routing.
  3. Flesh out chat stickers and the special boost mechanic per the RFC so gameplay- and UX-level promises match the
     document.