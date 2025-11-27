# Host Chat Message Duplicate Fix

## Issue
When the host sends a chat message, spectators receive it twice:
```
[CHAT] Host: hi spectator
[CHAT] Host: hi spectator
```

## Root Cause Analysis

When the host sends a chat message via `HostPeer.send_chat_message()`:
1. It creates a ChatMessage with a sequence number
2. It sends to joiner (if connected) using the same message object
3. It broadcasts to all spectators via `_broadcast_to_spectators()`

The problem was that `_broadcast_to_spectators()` was sending the same message object to all spectators. If the message was somehow received back by the host (through retransmission or network loopback), it could be processed and broadcast again.

Additionally, when the host broadcasts messages from other peers (joiner, spectator), it creates new messages with new sequence numbers in `_handle_chat_message_with_broadcast()`, but when broadcasting its own messages, it was using the original message object.

## Solution

Updated `_broadcast_to_spectators()` to create new message objects with unique sequence numbers for chat messages, similar to how `_handle_chat_message_with_broadcast()` handles forwarded messages.

### Changes Made

**File: `src/peer.py`**

**Method: `HostPeer._broadcast_to_spectators()`**

Before:
```python
def _broadcast_to_spectators(self, message: Message):
    for spectator_addr in self.spectators:
        try:
            self.send_message(message, spectator_addr)
        except Exception as e:
            print(f"Failed to send to spectator {spectator_addr}: {e}")
```

After:
```python
def _broadcast_to_spectators(self, message: Message):
    for spectator_addr in self.spectators:
        try:
            # For chat messages, create a new message with a new sequence number
            # to avoid duplicate detection issues and ensure each recipient gets a unique message
            if message.message_type == MessageType.CHAT_MESSAGE:
                from messages import ChatMessage
                broadcast_msg = ChatMessage(
                    sender_name=message.sender_name,
                    content_type=message.content_type,
                    message_text=getattr(message, 'message_text', None),
                    sticker_data=getattr(message, 'sticker_data', None),
                    sequence_number=self.reliability.get_next_sequence_number()
                )
                self.send_message(broadcast_msg, spectator_addr)
            else:
                # For non-chat messages, send the original message
                self.send_message(message, spectator_addr)
        except Exception as e:
            print(f"Failed to send to spectator {spectator_addr}: {e}")
```

## How It Works Now

1. **Host sends message:**
   - Creates ChatMessage with sequence number X
   - Sends to joiner (if connected) with sequence number X
   - Broadcasts to spectators, creating new messages with unique sequence numbers (Y, Z, etc.)

2. **Each spectator receives:**
   - A unique message with a unique sequence number
   - The original sender_name is preserved
   - No duplicate detection issues

3. **Benefits:**
   - Each message has a unique sequence number per recipient
   - Prevents false duplicate detection
   - Ensures messages are properly deduplicated
   - Maintains correct sender attribution

## Testing

To verify the fix:
1. Start host, joiner, and spectator
2. Host sends a chat message: `/chat hi spectator`
3. Spectator should receive the message exactly once: `[CHAT] Host: hi spectator`
4. No duplicate messages should appear

The fix ensures that each spectator receives a unique message instance, preventing duplicate detection issues and ensuring clean message delivery.

