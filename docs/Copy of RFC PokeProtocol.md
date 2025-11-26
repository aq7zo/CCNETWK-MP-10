# **Request for Comments: P2P Pokémon Battle Protocol (PokeProtocol) over UDP**

Document Type: Protocol Specification  
Status: Draft

## **Abstract**

This document specifies the Peer-to-Peer Pokémon Battle Protocol (PokeProtocol) using UDP as its transport layer, with an added feature for peer-to-peer text chat that now includes an option for sending stickers. This protocol is designed for conducting a turn-based Pokémon battle between two independent peers over a network. It defines a structured messaging format and a state machine, incorporating a custom reliability layer to ensure a synchronized view of the battle and reliable delivery of chat messages despite UDP's connectionless nature. This revision introduces a granular, four-step handshake for each turn, requiring explicit agreement on attack, defense, and calculation to prevent discrepancies. It also introduces three distinct communication roles: a **Peer-to-Peer** mode for direct one-to-one communication, a **Broadcast** mode for announcing battle availability on a local network, and a new **Spectator** role. Finally, it refines the damage calculation formula to include separate **Special Attack** and **Special Defense** stats. Players can use a limited number of special attack and special defense boosts during the battle, which are defined during the setup phase.

## **1\. Introduction**

The objective of this PokeProtocol revision is to provide a low-overhead, platform-agnostic, and unambiguous method for simulating Pokémon battles in two applications. By leveraging UDP, this protocol minimizes latency by forgoing TCP's built-in reliability and flow control. Instead, it addresses the challenges of game state synchronization in a decentralized environment by implementing a custom reliability and ordering mechanism at the application layer. The addition of a chat feature, which now supports stickers, enhances the interactive experience without impacting the core battle mechanics.

## **2\. Terminology**

* **Peer:** An application instance participating in a battle.  
* **Host Peer:** The peer that initiates the connection and game. It is responsible for listening for datagrams from the Joiner Peer.  
* **Joiner Peer:** The peer that sends a connection request to the Host Peer to start the battle.  
* **Spectator Peer:** A peer that joins an active battle to observe. Spectators can send and receive chat messages but cannot influence the battle state.  
* **Battle State:** The collective information representing the current state of the battle, including Pokémon health, status effects, and turn order.

## **3\. Protocol Architecture**

The PokeProtocol over UDP is built on a peer-to-peer architecture using UDP datagrams.

* **Transport Layer:** **UDP** (User Data Protocol) MUST be used.  
* **Communication Modes:** This protocol supports three primary communication modes:  
  * **Peer-to-Peer Mode:** Messages are sent directly from one peer to another using a known IP address and port. This is the standard mode for all battle-related messages once the connection is established.  
  * **Broadcast Mode:** Messages are sent to a broadcast address (e.g., 255.255.255.255) to be received by all peers on a local network. This mode can be used for initial peer discovery or for announcing a game's presence.  
  * **Spectator Mode:** A peer can join an existing battle as a spectator. They receive all battle and chat messages, but are restricted from sending battle-related commands. They can, however, send CHAT\_MESSAGEs.  
* **Connection Process:** Since UDP is connectionless, a logical connection must be established.  
  1. The Host Peer creates a UDP socket and begins listening on a designated port.  
  2. The Joiner Peer creates a UDP socket and sends a HANDSHAKE\_REQUEST message to the Host Peer's IP address and port. A Spectator Peer would send a SPECTATOR\_REQUEST instead.  
  3. The Host Peer, upon receiving a request, responds with a HANDSHAKE\_RESPONSE message.  
  4. All peers are now considered logically connected and ready for their respective roles.


## **4\. Message Format and Types**

All communication between peers MUST be in a plain text format, with a single message per UDP datagram. Messages are composed of a series of newline-separated key: value pairs. The message\_type field is mandatory for all messages.

### **4.1. HANDSHAKE\_REQUEST**

This message is sent by the Joiner Peer to initiate a logical connection as a player.

**Format:**

```shell
message_type: HANDSHAKE_REQUEST
```

### 

### **4.2. HANDSHAKE\_RESPONSE**

This message is sent by the Host Peer to acknowledge a connection request.

* message\_type: "HANDSHAKE\_RESPONSE"  
* seed: A random integer that will be used to seed the random number generator on both peers to ensure synchronized damage calculation.

**Format:**

```shell
message_type: HANDSHAKE_RESPONSEseed: 12345
```

### **4.3. SPECTATOR\_REQUEST**

This message is sent by a peer to initiate a logical connection as a spectator.

**Format:**

### 

```shell
message_type: SPECTATOR_REQUEST
```

### **4.4. BATTLE\_SETUP**

This message is sent by both playing peers after the handshake to exchange initial Pokémon data and define the communication mode for the battle.

* message\_type: "BATTLE\_SETUP"  
* communication\_mode: A string indicating the mode of communication for the battle. Valid values are "P2P" and "BROADCAST".  
* pokemon\_name: The name of the peer's Pokémon.  
* stat\_boosts: An object containing the player's allocation of a limited number of special attack and special defense uses.  
* pokemon: An object containing the peer's chosen Pokémon data.

**Format:**

```shell
message_type: BATTLE_SETUPcommunication_mode: P2Ppokemon_name: Pikachustat_boosts: { "special_attack_uses": 5, "special_defense_uses": 5 }
```

### **4.5. ATTACK\_ANNOUNCE**

This message is sent by the peer whose turn it is to announce their move choice.

* message\_type: "ATTACK\_ANNOUNCE"  
* move\_name: The name of the chosen move.  
* sequence\_number: A unique, monotonically increasing integer for this message.

**Format:**

```shell
message_type: ATTACK_ANNOUNCEmove_name: Thunderboltsequence_number: 5
```

### **4.6. DEFENSE\_ANNOUNCE**

This message is sent by the defending peer to acknowledge the opponent's ATTACK\_ANNOUNCE and signal readiness to process the turn.

* message\_type: "DEFENSE\_ANNOUNCE"  
* sequence\_number: A unique, monotonically increasing integer for this message.

**Format:**

```shell
message_type: DEFENSE_ANNOUNCEsequence_number: 6
```

### **4.7. CALCULATION\_REPORT**

This message is sent by both players to report the results of their independent damage calculation for the turn.

* message\_type: "CALCULATION\_REPORT"  
* attacker: The name of the Pokémon that attacked.  
* move\_used: The name of the move that was used.  
* remaining\_health: The remaining health of the attacking Pokémon.  
* damage\_dealt: The amount of damage inflicted.  
* defender\_hp\_remaining: The defender's remaining HP after the attack.  
* status\_message: A descriptive string of the turn's events (e.g., "Pikachu used Thunderbolt\! It was super effective\!").  
* sequence\_number: A unique, monotonically increasing integer for this message.

**Format:**

```shell
message_type: CALCULATION_REPORTattacker: Pikachumove_used: Thunderboltremaining_health: 90damage_dealt: 80defender_hp_remaining: 20status_message: Pikachu used Thunderbolt! It was super effective!sequence_number: 7
```

### **4.8. CALCULATION\_CONFIRM**

This message is sent by a player to confirm that their opponent's CALCULATION\_REPORT matches their own.

* message\_type: "CALCULATION\_CONFIRM"  
* sequence\_number: A unique, monotonically increasing integer for this message.

**Format:**

```shell
message_type: CALCULATION_CONFIRMsequence_number: 8
```

### **4.9. RESOLUTION\_REQUEST**

This message is sent by a player when a calculation discrepancy is detected. It contains the sender's calculated values for the turn.

* message\_type: "RESOLUTION\_REQUEST"  
* attacker: The name of the Pokémon that attacked.  
* move\_used: The name of the move that was used.  
* damage\_dealt: The amount of damage inflicted as calculated by the sending peer.  
* defender\_hp\_remaining: The defender's remaining HP as calculated by the sending peer.  
* sequence\_number: A unique, monotonically increasing integer for this message.

**Format:**

```shell
message_type: RESOLUTION_REQUESTattacker: Pikachumove_used: Thunderboltdamage_dealt: 80defender_hp_remaining: 20sequence_number: 9
```

### **4.10. GAME\_OVER**

This message is sent by a player when their opponent's Pokémon has fainted.

* message\_type: "GAME\_OVER"  
* winner: The name of the Pokémon that won.  
* loser: The name of the Pokémon that fainted.  
* sequence\_number: A unique, monotonically increasing integer for this message.

```shell
message_over: GAME_OVERwinner: Pikachuloser: Charmandersequence_number: 10
```

### **4.11. CHAT\_MESSAGE**

This message is used for sending a plain text chat message or a sticker between peers. It can be sent by any peer (Host, Joiner, or Spectator) at any time, independently of the turn-based battle logic.

* message\_type: "CHAT\_MESSAGE"  
* sender\_name: The name of the peer sending the message.  
* content\_type: A string that specifies the content type of the message. Valid values are "TEXT" or "STICKER".  
* message\_text: (Optional) The content of the chat message, used when content\_type is "TEXT".  
* sticker\_data: (Optional) A Base64 encoded string of the sticker data. The sticker dimensions MUST be 320px x 320px and the file size should be less than 10MB. Implementations should be aware that sending large messages (over 1.5 KB) over UDP may require fragmentation at the IP layer, which can affect network performance and reliability.  
* sequence\_number: A unique, monotonically increasing integer for this message.

**Format:**

// Example of a text message

```shell
message_type: CHAT_MESSAGEsender_name: Player1content_type: TEXTmessage_text: Good luck, have fun!sequence_number: 11// Example of a sticker message (abbreviated Base64 data)message_type: CHAT_MESSAGEsender_name: Player2content_type: STICKERsticker_data: iVBORw0KGgoAAAANSUhEUgAAB...sequence_number: 12
```

## **5\. State Management and Game Flow**

The battle follows a simple state machine, enhanced with a reliability layer. Chat messages are handled as an asynchronous overlay to this state machine.

### **5.1. Reliability Layer**

To handle UDP's unreliable nature, the following is required:

* **Sequence Numbers:** Every non-ACK message MUST include a sequence\_number.  
* **Acknowledgements:** Upon receiving a message with a sequence number, the peer MUST send an ACK message with the corresponding ack\_number.  
* **Retransmission:** If a peer sends a message but does not receive an ACK within a predefined timeout, it MUST retransmit the message. A retransmission counter should be maintained for each message. If the maximum number of retries is reached without receiving an ACK, the peer SHOULD assume the connection has been lost and terminate the battle. The recommended timeout is **500 milliseconds**, and the recommended maximum number of retries is **3**.

### **5.2. Game Flow**

1. **Initial State (SETUP):**  
   * Host and Joiner Peers connect via the handshake process. The Host sends a HANDSHAKE\_RESPONSE with a seed. Both peers use this seed for their random number generators.  
   * Both playing Peers send a BATTLE\_SETUP message with their chosen Pokémon data and the desired communication\_mode.  
   * Upon successfully exchanging BATTLE\_SETUP messages, each peer transitions to the WAITING\_FOR\_MOVE state. Spectator Peers, upon connecting, receive all battle messages but do not take turns.  
2. **Turn-Based State (WAITING\_FOR\_MOVE):**  
   * The Host Peer is designated to go first.  
   * The acting peer sends an ATTACK\_ANNOUNCE message with a new sequence number.  
   * The defending peer must wait for a valid ATTACK\_ANNOUNCE message. Upon receiving it, the defender sends a DEFENSE\_ANNOUNCE message, confirming receipt and signaling readiness for the next phase.  
   * Upon receiving the DEFENSE\_ANNOUNCE message, both players independently apply the damage and transition to the PROCESSING\_TURN state.

   

3. **Turn Processing State (PROCESSING\_TURN):**  
   * Each player independently performs the damage calculation, using the appropriate attack and defense stats based on the move's damage\_category.  
   * Each player then sends a CALCULATION\_REPORT message with a new sequence number to the other player. This message acts as a checksum.  
   * **Discrepancy Resolution:**  
     * If the received CALCULATION\_REPORT **matches** the peer's local calculation, the peer sends a CALCULATION\_CONFIRM message, and the turn order reverses, returning to the WAITING\_FOR\_MOVE state. The new field remaining\_health can be used to perform additional integrity checks on the battle state.  
     * If the received CALCULATION\_REPORT **does not match** the peer's local calculation, the peer MUST send a RESOLUTION\_REQUEST message containing its own calculated values. It should then wait for a response.  
     * The other peer, upon receiving a RESOLUTION\_REQUEST, must re-evaluate the turn based on the received data. If it agrees with the RESOLUTION\_REQUEST's values, it sends an ACK and updates its state to match. If it still disagrees, this indicates a fundamental error, and the battle SHOULD terminate.  
4. **Chat Functionality:**  
   * A peer can send a CHAT\_MESSAGE at any time, regardless of the current battle state.  
   * Chat messages are handled separately from the turn-based logic.  
   * Upon receiving a CHAT\_MESSAGE, the peer should display the message to the user and send an ACK to confirm receipt.  
5. **Final State (GAME\_OVER):**  
   * When a Pokémon's HP drops to zero or below, the peer whose opponent has fainted sends a GAME\_OVER message.  
   * This message also requires a sequence number and acknowledgment.  
   * Upon receiving this message, the battle ends.

## **6\. Damage Calculation**

To ensure synchronization, both peers MUST use the exact same damage calculation formula. The formula uses the appropriate attack and defense stats depending on the move's damage\_category.

[![][image1]](https://www.codecogs.com/eqnedit.php?latex=Damage%20%3D%20%5Cfrac%7BBasePower%20%5Ctimes%20AttackerStat%20%5Ctimes%20Type1Effectiveness%20%5Ctimes%20Type2Effectiveness%7D%7BDefenderStat%7D#0)

* **AttackerStat**: The attacking Pokémon's **Attack** stat for physical moves, or **SpecialAttack** stat for special moves.  
* **DefenderStat**: The defending Pokémon's **PhysicalDefense** stat for physical moves, or **SpecialDefense** stat for special moves.  
* **BasePower**: The power attribute of the move.  
* **Type1Effectiveness**: A multiplier based on the attacking move's type against the defending Pokémon's primary type.  
* **Type2Effectiveness**: A multiplier based on the attacking move's type against the defending Pokémon's secondary type. If the Pokémon only has one type, this value is 1.0.  
* **PhysicalDefense**: The physical defense stat of the defending Pokémon.  
* **SpecialAttack**: The special attack stat of the attacking Pokémon.  
* **SpecialDefense**: The special defense stat of the defending Pokémon.  
* **stat\_boosts**: An object containing the player's allocation of a limited number of special attack and special defense uses. These are a consumable resource for the player during the battle.

The given Pokémon stats can be found in the given CSV file.

**Example:** If a Fire-type move attacks a dual-type Pokémon that is Grass/Water:

* The move is super-effective against the Grass type (2.0).  
  * The move is not very effective against the Water type (0.5).  
  * The final TypeEffectiveness multiplier would be 2.0x0.5=1.0.


[image1]: <data:image/png;base64,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>