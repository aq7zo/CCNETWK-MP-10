# Complete Testing Guide for PokeProtocol

This guide covers all testing methods to verify the program works correctly and is RFC-compliant.

---

## Quick Start: Automated Tests

**Run all automated tests (no network required):**

```bash
python tests/test_suite.py
```

**Expected Output:**
```
Ran 21 tests in X.XXXs
OK
```

**What it tests:**
- ✅ Pokemon data loading (3 tests)
- ✅ Move database (3 tests)  
- ✅ Message serialization (5 tests)
- ✅ Reliability layer (3 tests)
- ✅ Battle state machine (3 tests)
- ✅ Damage calculation (4 tests)
- ✅ Full integration (1 test)

---

## Manual Testing: Complete Battle Flow

### Test 1: Basic Host-Joiner Battle

**Setup:** Two terminals on same machine (or two machines on same network)

**Terminal 1 (Host):**
```bash
python scripts/interactive_battle.py host
```
- Enter port: `8888` (or press Enter for default)
- Select Pokémon: `Pikachu` (or any Pokémon)
- When prompted, select moves (1-4)

**Terminal 2 (Joiner):**
```bash
python scripts/interactive_battle.py joiner
```
- Enter host IP: `127.0.0.1` (for localhost) or host's IP address
- Enter host port: `8888`
- Enter local port: `8889` (or press Enter for default)
- Select Pokémon: `Charmander` (or any Pokémon)
- When prompted, select moves (1-4)

**What to verify:**
- ✅ Host shows "Joiner connected!"
- ✅ Both see opponent's Pokémon selection
- ✅ Turn-based battle progresses correctly
- ✅ Damage calculations match on both sides
- ✅ HP updates correctly
- ✅ Game ends when HP reaches 0
- ✅ Winner/loser displayed correctly
- ✅ Rematch prompt appears

---

### Test 2: Spectator Mode

**Setup:** Three terminals (or three machines)

**Terminal 1 (Host):**
```bash
python scripts/interactive_battle.py host
```

**Terminal 2 (Joiner):**
```bash
python scripts/interactive_battle.py joiner
```

**Terminal 3 (Spectator):**
```bash
python scripts/interactive_battle.py spectator
```
- Enter host IP: `127.0.0.1` (or host's IP)
- Enter host port: `8888`
- Enter local port: `8890`

**What to verify:**
- ✅ Spectator connects successfully
- ✅ Spectator sees both Pokémon selections
- ✅ Spectator sees all attacks and damage
- ✅ Spectator sees HP updates for both players
- ✅ Spectator sees game over message
- ✅ Spectator sees rematch decisions
- ✅ Spectator closes when rematch declined

---

### Test 3: Error Handling & Retry Logic

**Test Port Conflicts:**

**Terminal 1:**
```bash
python scripts/interactive_battle.py host
# Use port 8888
```

**Terminal 2 (try same port):**
```bash
python scripts/interactive_battle.py host
# Try port 8888 again
```

**What to verify:**
- ✅ Error message: "Port 8888 is already in use!"
- ✅ Prompt to try different port
- ✅ Can retry with new port

**Test Connection Failures:**

**Terminal 1:** Don't start host yet

**Terminal 2:**
```bash
python scripts/interactive_battle.py joiner
# Enter wrong IP or port
```

**What to verify:**
- ✅ Connection fails with error message
- ✅ Troubleshooting tips displayed
- ✅ Prompt to retry with different settings
- ✅ Can re-enter IP/port and retry

---

### Test 4: Complete Turn Flow Verification

**Steps:**
1. Start host and joiner
2. Select Pokémon
3. **Host's turn:**
   - Select move
   - Verify `[DEBUG] Host sent AttackAnnounce` appears
   - Verify joiner receives `[DEBUG] Joiner received AttackAnnounce`
   - Verify `[DEBUG] Sent DefenseAnnounce` on joiner
   - Verify `[DEBUG] Host sent CalculationReport`
   - Verify `[DEBUG] Joiner sent CalculationReport`
   - Verify `[DEBUG] Host: Calculations match!`
   - Verify turn completes

4. **Joiner's turn:**
   - Same verification steps
   - Verify turn order switches correctly

**What to verify:**
- ✅ All four steps of turn handshake occur
- ✅ Debug messages show correct flow
- ✅ State transitions correctly
- ✅ Damage applied correctly

---

### Test 5: Damage Calculation Synchronization

**Steps:**
1. Start battle with known Pokémon (e.g., Pikachu vs Charmander)
2. Use same move multiple times
3. Compare damage values on both terminals

**What to verify:**
- ✅ Both peers show identical damage
- ✅ Both peers show identical HP after each turn
- ✅ Type effectiveness calculated correctly
- ✅ Status messages match

---

### Test 6: Game Over & Rematch

**Steps:**
1. Battle until one Pokémon faints
2. Verify game over message
3. Test rematch scenarios:

**Scenario A: Both want rematch**
- Host: Enter `Y`
- Joiner: Enter `Y`
- **Verify:** New battle starts

**Scenario B: One declines**
- Host: Enter `Y`
- Joiner: Enter `N`
- **Verify:** Battle ends gracefully

**Scenario C: Both decline**
- Host: Enter `N`
- Joiner: Enter `N`
- **Verify:** Both disconnect

**What to verify:**
- ✅ Game over detected correctly
- ✅ Winner/loser displayed
- ✅ Rematch prompt works
- ✅ Both players wait for opponent's decision
- ✅ Program closes gracefully when declined

---

### Test 7: Debug Output Verification

**Enable debug mode and verify:**

**What to look for:**
- ✅ `[DEBUG] HOST received: MESSAGE_TYPE, seq=X, from=ADDRESS`
- ✅ `[DEBUG] HOST sent MESSAGE_TYPE, seq=X`
- ✅ `[DEBUG] Host _handle_attack_announce: ...`
- ✅ `[DEBUG] Host: Processing AttackAnnounce, sending DefenseAnnounce...`
- ✅ `[DEBUG] Host: Calculations match! Sending confirm...`
- ✅ `[DEBUG] HOST retransmitting MESSAGE_TYPE, seq=X` (if needed)

**Verify debug covers:**
- Message sending/receiving
- State transitions
- Turn processing
- Retransmissions
- Error handling

---

### Test 8: Network Reliability

**Test Retransmission:**

1. Start battle
2. Monitor for `[DEBUG] retransmitting` messages
3. Verify messages eventually get through

**Test Duplicate Detection:**

1. Send same message twice (if possible)
2. Verify duplicate is ignored
3. Check debug output shows duplicate detection

**What to verify:**
- ✅ Messages retransmitted if no ACK
- ✅ Duplicates detected and ignored
- ✅ Sequence numbers increment correctly
- ✅ ACKs sent for all messages

---

### Test 9: Chat Functionality (if implemented)

**Steps:**
1. During battle, send chat message
2. Verify message appears on other side
3. Test during different battle states

**What to verify:**
- ✅ Chat works independently of battle state
- ✅ Messages delivered reliably
- ✅ Can send/receive during any state

---

### Test 10: Multiple Battles (Rematch)

**Steps:**
1. Complete one battle
2. Both agree to rematch
3. Start new battle
4. Verify fresh state (HP reset, etc.)

**What to verify:**
- ✅ New battle starts correctly
- ✅ Pokémon HP reset to full
- ✅ State machine resets properly
- ✅ No leftover state from previous battle

---

## Testing Checklist

### Core Functionality
- [ ] Host can start and listen for connections
- [ ] Joiner can connect to host
- [ ] Handshake completes successfully
- [ ] Battle setup exchanges Pokémon data
- [ ] Turn-based battle works correctly
- [ ] Damage calculations match on both sides
- [ ] Game over detected correctly
- [ ] Rematch system works

### Error Handling
- [ ] Port conflicts handled gracefully
- [ ] Connection failures allow retry
- [ ] Invalid input handled correctly
- [ ] Network errors don't crash program
- [ ] Timeout handling works

### Debugging
- [ ] Debug messages appear for all major events
- [ ] Message flow is traceable
- [ ] State transitions logged
- [ ] Errors logged with context

### Spectator Mode
- [ ] Spectator can connect
- [ ] Spectator sees all battle events
- [ ] Spectator sees Pokémon selections
- [ ] Spectator sees attacks and damage
- [ ] Spectator sees game over
- [ ] Spectator sees rematch decisions
- [ ] Spectator closes when battle ends

### RFC Compliance
- [ ] All message types implemented
- [ ] Sequence numbers on all messages
- [ ] ACKs sent for all messages
- [ ] Retransmission works (500ms timeout, 3 retries)
- [ ] State machine follows RFC flow
- [ ] Damage calculation matches RFC formula
- [ ] Stat boosts work as consumable resources

---

## Quick Test Commands

### Run Automated Tests
```bash
python tests/test_suite.py
```

### Test Host Mode
```bash
python scripts/interactive_battle.py host
```

### Test Joiner Mode
```bash
python scripts/interactive_battle.py joiner
```

### Test Spectator Mode
```bash
python scripts/interactive_battle.py spectator
```

### Test with Debug Output
All debug messages are enabled by default. Look for `[DEBUG]` prefixed messages.

---

## Troubleshooting Test Failures

### Connection Issues
- **Problem:** Joiner can't connect to host
- **Solution:** 
  - Verify host is running first
  - Check IP address is correct
  - Check firewall settings
  - Try `127.0.0.1` for localhost testing

### Port Already in Use
- **Problem:** Port conflict error
- **Solution:**
  - Use different port
  - Close other instances
  - Program will prompt to retry with new port

### Messages Not Received
- **Problem:** Messages seem lost
- **Solution:**
  - Check debug output for retransmissions
  - Verify network connectivity
  - Check firewall allows UDP traffic

### Damage Mismatch
- **Problem:** Different damage on each side
- **Solution:**
  - Verify both peers use same seed
  - Check Pokémon stats match
  - Verify move data is identical

---

## Expected Test Results

### Automated Tests
```
Ran 21 tests in X.XXXs
OK
```

### Manual Battle Test
- ✅ Connection established
- ✅ Battle progresses turn-by-turn
- ✅ Damage matches on both sides
- ✅ Game ends when HP reaches 0
- ✅ Rematch works correctly

### Spectator Test
- ✅ Spectator connects
- ✅ Sees all battle events
- ✅ Closes when battle ends

---

## Test Report Template

After testing, document results:

```
Test Date: [Date]
Tester: [Name]

Automated Tests: ✅ PASS / ❌ FAIL
- Tests run: 21
- Tests passed: [X]
- Tests failed: [X]

Manual Tests:
- Host-Joiner Battle: ✅ / ❌
- Spectator Mode: ✅ / ❌
- Error Handling: ✅ / ❌
- Rematch System: ✅ / ❌
- Debug Output: ✅ / ❌

Issues Found: [List any issues]

Overall Status: ✅ COMPLIANT / ❌ NON-COMPLIANT
```

---

*For detailed RFC compliance verification, see `docs/RFC_COMPLIANCE.md`*

