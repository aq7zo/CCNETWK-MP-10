# Testing Guide for PokeProtocol

## Testing Requirements

### Minimum Configuration
**Two participants**: One Host + One Joiner

The PokeProtocol is designed as a **two-player battle system** with optional spectator support.

### Quick Start: Automated Testing
**No participants needed!** Run automated unit tests on a single machine:

```bash
python test_suite.py
```

This runs 21 comprehensive tests covering all components:
- Pokemon data loading (3 tests)
- Move database (3 tests)
- Message serialization (5 tests)
- Reliability layer (3 tests)
- Battle state machine (3 tests)
- Damage calculation (4 tests)
- Full integration (1 test)

**Result:** All 21 tests pass ✅

## Setup Options

### Option 1: Two Separate Machines (Recommended)
This tests the full network functionality.

**Machine A (Host):**
```bash
python example_battle.py host
```

**Machine B (Joiner):**
```bash
python example_battle.py joiner
```

**Requirements:**
- Both machines on same network
- Host's IP address (use `ipconfig` on Windows or `ifconfig` on Linux/Mac)
- Firewall allowing UDP traffic on ports 8888 and 8889

### Option 2: Same Machine with Two Terminals
This tests protocol logic locally.

**Terminal 1 (Host):**
```bash
python example_battle.py host
```

**Terminal 2 (Joiner):**
```bash
python example_battle.py joiner
```

**Requirements:**
- Two command-line windows
- Default: Joiner connects to `127.0.0.1` (localhost)

### Option 3: Local Network Testing
For testing across a local network.

**Host Configuration:**
1. Find your IP: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
2. Start host: `python example_battle.py host`

**Joiner Configuration:**
1. Edit `example_battle.py` joiner section or pass IP as parameter
2. Connect to host's IP address
3. Start joiner: `python example_battle.py joiner`

## Testing Scenarios

### Basic Functionality Tests

#### 1. Connection Test
**Objective:** Verify handshake process

**Steps:**
1. Host starts listening
2. Joiner attempts connection
3. Verify both peers show "Connected"

**Expected Result:** Connection established, seed exchanged

#### 2. Battle Setup Test
**Objective:** Verify Pokémon selection and exchange

**Steps:**
1. Both peers select Pokémon (e.g., Pikachu vs Charmander)
2. Verify BATTLE_SETUP messages exchanged
3. Check both sides see opponent's Pokémon

**Expected Result:** Setup complete, battle ready

#### 3. Turn Execution Test
**Objective:** Verify four-step handshake

**Steps:**
1. Host (goes first) selects move
2. Verify ATTACK_ANNOUNCE sent
3. Verify DEFENSE_ANNOUNCE received
4. Check CALCULATION_REPORT from both sides
5. Verify CALCULATION_CONFIRM exchanged

**Expected Result:** Turn completes, damage applied, turn switches

#### 4. Damage Calculation Test
**Objective:** Verify synchronized calculations

**Steps:**
1. Execute several turns with different type matchups
2. Check that both peers show identical damage
3. Verify HP updates match on both sides

**Expected Result:** Identical calculations, synchronized state

#### 5. Game Over Test
**Objective:** Verify end game handling

**Steps:**
1. Battle until one Pokémon faints (HP ≤ 0)
2. Verify GAME_OVER message sent
3. Check winner announcement

**Expected Result:** Game ends gracefully, winner displayed

### Advanced Tests

#### 6. Network Reliability Test
**Objective:** Test ACK/retry mechanisms

**Setup:** Use packet loss simulation or poor network conditions

**Steps:**
1. Monitor message retransmissions
2. Verify ACK handling
3. Check sequence number tracking
4. Test timeout and retry limits

**Expected Result:** Reliable delivery despite packet loss

#### 7. Chat Functionality Test
**Objective:** Verify chat messaging

**Steps:**
1. Send chat messages from both sides
2. Verify messages appear on receiver
3. Test during different battle states

**Expected Result:** Chat works independently of battle

#### 8. Discrepancy Resolution Test
**Objective:** Test calculation mismatch handling

**Note:** This may require forced discrepancy or code modification

**Steps:**
1. Force a calculation mismatch
2. Verify RESOLUTION_REQUEST sent
3. Check resolution mechanism

**Expected Result:** Discrepancy resolved, battle continues

### Stress Tests

#### 9. Rapid Turn Test
**Objective:** Test under high message frequency

**Steps:**
1. Turn off delays/sleeps in code
2. Execute many turns quickly
3. Monitor for deadlocks or missed messages

**Expected Result:** System remains stable

#### 10. Long Battle Test
**Objective:** Test extended gameplay

**Steps:**
1. Battle with high HP Pokemon
2. Execute 20+ turns
3. Monitor memory usage and state

**Expected Result:** No memory leaks, stable performance

## Testing with Spectators

### Spectator Setup (Optional)
The protocol supports spectator mode, though not fully implemented in examples.

**Configuration:**
- **Machine 1:** Host
- **Machine 2:** Joiner  
- **Machine 3:** Spectator (optional)

**Implementation:** Modify example code to include SpectatorPeer

## Automated Testing Recommendations

### Unit Tests (Not Yet Implemented)
Would test individual components:
- Pokemon data loading
- Move database
- Message serialization
- Damage calculation
- State machine transitions
- Reliability layer

### Integration Tests
Would test full flows:
- Complete battle from setup to finish
- All message exchanges
- Error scenarios

### Network Simulation Tests
Would test:
- Packet loss scenarios
- Latency conditions
- Out-of-order delivery
- Duplicate packets

## Troubleshooting

### Connection Issues
**Problem:** Joiner can't connect to host

**Solutions:**
- Verify both machines on same network
- Check IP address is correct
- Ensure firewall allows UDP ports
- Verify host is listening before joiner connects
- Try localhost (127.0.0.1) first

### Timeout Issues
**Problem:** Messages timeout

**Solutions:**
- Increase timeout values (default 500ms)
- Check network quality
- Verify reliability layer is running
- Check for firewall blocking

### State Issues
**Problem:** Battle state desynchronizes

**Solutions:**
- Verify both peers use same seed
- Check damage calculation matches
- Ensure all messages ACKed
- Restart both peers

## Manual Testing Checklist

### Pre-Test
- [ ] Both machines have project files
- [ ] Python 3.7+ installed
- [ ] Network connectivity verified
- [ ] No conflicts on ports 8888/8889

### Connection
- [ ] Host starts successfully
- [ ] Joiner connects within 30 seconds
- [ ] Seed exchanged correctly

### Setup
- [ ] Host selects Pokemon
- [ ] Joiner selects Pokemon
- [ ] Both see opponent's Pokemon

### Battle
- [ ] Host's first turn executes
- [ ] Damage calculated correctly
- [ ] HP updates on both sides
- [ ] Turn switches correctly
- [ ] Joiner's turn executes

### End Game
- [ ] Game over triggers
- [ ] Winner announced
- [ ] Both sides see results

### Bonus Tests
- [ ] Chat messages work
- [ ] Multiple battles possible
- [ ] Disconnection handled gracefully

## Performance Benchmarks

### Expected Timings
- Handshake: < 1 second
- Turn execution: ~1-2 seconds
- Chat delivery: < 500ms
- Retransmission: 500ms per attempt

### Resource Usage
- Memory: < 50MB per peer
- CPU: Minimal (< 5%)
- Network: < 1KB per message

## Success Criteria

A successful test should demonstrate:
1. ✅ Full connection and handshake
2. ✅ Complete battle from start to finish
3. ✅ Synchronized damage calculations
4. ✅ All message types working
5. ✅ Graceful game end
6. ✅ Chat functionality
7. ✅ Reliability under normal conditions

## Minimum Viable Test

**Quick Verification (5 minutes):**
1. Start host
2. Start joiner
3. Complete 2-3 turns
4. Verify damage matches
5. End battle

If this works, core protocol is functional!

## Conclusion

**You need exactly 2 people** to test effectively:
- One as Host
- One as Joiner

Optional:
- Third person as Spectator (if implemented)

Local testing (same machine) is sufficient for protocol validation. Network testing (different machines) validates full UDP functionality.

