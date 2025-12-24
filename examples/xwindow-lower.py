#!/usr/bin/env python3
from Xlib import X, display, protocol
import time

def find_client_window(d, frame_window):
    """Find the client window inside a Compiz frame window.

    Compiz structure: Frame -> Wrapper -> Client
    The client window is registered in _NET_CLIENT_LIST.
    """
    NET_CLIENT_LIST = d.intern_atom('_NET_CLIENT_LIST')
    root = d.screen().root

    try:
        client_list = root.get_full_property(NET_CLIENT_LIST, X.AnyPropertyType)
        if not client_list:
            return None

        # Get frame's children (one of them is the wrapper containing the client)
        frame_tree = frame_window.query_tree()

        # Check each registered client window
        for client_id in client_list.value:
            client = d.create_resource_object('window', client_id)
            try:
                client_tree = client.query_tree()
                parent_id = client_tree.parent.id

                # Check if client's parent is one of the frame's children
                for frame_child in frame_tree.children:
                    if frame_child.id == parent_id:
                        return client  # Found it!
            except:
                continue
    except:
        pass

    return None

def is_desktop_or_dock(d, window):
    """Check if window is a desktop or dock window (shouldn't be lowered)."""
    WM_WINDOW_TYPE = d.intern_atom('_NET_WM_WINDOW_TYPE')
    WM_WINDOW_TYPE_DESKTOP = d.intern_atom('_NET_WM_WINDOW_TYPE_DESKTOP')
    WM_WINDOW_TYPE_DOCK = d.intern_atom('_NET_WM_WINDOW_TYPE_DOCK')

    try:
        window_type = window.get_full_property(WM_WINDOW_TYPE, X.AnyPropertyType)
        if window_type:
            for atom in window_type.value:
                if atom in [WM_WINDOW_TYPE_DESKTOP, WM_WINDOW_TYPE_DOCK]:
                    return True
    except:
        pass
    return False

def get_window_title(d, window):
    """Get the window title, trying _NET_WM_NAME first, then WM_NAME."""
    NET_WM_NAME = d.intern_atom('_NET_WM_NAME')
    UTF8_STRING = d.intern_atom('UTF8_STRING')

    # Try _NET_WM_NAME (UTF-8) first
    try:
        title_prop = window.get_full_property(NET_WM_NAME, UTF8_STRING)
        if title_prop and title_prop.value:
            return title_prop.value.decode('utf-8', errors='replace')
    except:
        pass

    # Fall back to WM_NAME
    try:
        title_prop = window.get_full_property(X.XA_WM_NAME, X.AnyPropertyType)
        if title_prop and title_prop.value:
            # WM_NAME might be STRING (Latin-1) or UTF8_STRING
            if isinstance(title_prop.value, bytes):
                return title_prop.value.decode('latin-1', errors='replace')
            else:
                return str(title_prop.value)
    except:
        pass

    return "(no title)"

d = display.Display()
root = d.screen().root

# Get window under cursor
pointer = root.query_pointer()
child_win = pointer.child

# Safety check: ensure we're not pointing at root window
if not child_win or child_win.id == root.id:
    print("No window under cursor (pointing at root window)")
    exit(0)

# Find top-level window (traverse up to root's child) - this is the frame
while True:
    parent = child_win.query_tree().parent
    if parent == root or parent.id == root.id:
        break
    child_win = parent

# Find the actual client window inside the frame
client_win = find_client_window(d, child_win)

if not client_win:
    print(f"Could not find client window for frame 0x{child_win.id:x}")
    exit(1)

# Safety check: don't lower desktop or dock windows
if is_desktop_or_dock(d, client_win):
    title = get_window_title(d, client_win)
    print(f"Refusing to lower desktop/dock window 0x{client_win.id:x} - {title}")
    exit(0)

# Send _NET_RESTACK_WINDOW ClientMessage with the CLIENT window ID
RESTACK = d.intern_atom('_NET_RESTACK_WINDOW')

ev = protocol.event.ClientMessage(
    window = client_win,
    client_type = RESTACK,
    data = (32, [2, 0, X.Below, 0, 0])  # source=2, sibling=0, mode=Below
)

root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
d.flush()

lowered_title = get_window_title(d, client_win)
print(f"Lowered window 0x{client_win.id:x} - {lowered_title}")

# Synchronize with the X server to ensure the lower operation is processed
# This prevents race conditions before querying for the window underneath
d.sync()

# Now find and activate the window under the cursor after lowering
# Query pointer again to get the newly revealed window
pointer = root.query_pointer()
new_child = pointer.child

# Ensure we have a valid window that's not root and not the same window we just lowered
if not new_child or new_child.id == root.id:
    print("No window revealed underneath (pointing at root)")
    exit(0)

# Find top-level window for the newly revealed window
while True:
    parent = new_child.query_tree().parent
    if parent == root or parent.id == root.id:
        break
    new_child = parent

# Find its client window
new_client = find_client_window(d, new_child)

if not new_client:
    print(f"Could not find client window for revealed frame 0x{new_child.id:x}")
    exit(0)

# Verify this is actually a different window
if new_client.id == client_win.id:
    print("Same window still under cursor (no window revealed)")
    exit(0)

# Send _NET_ACTIVE_WINDOW to focus the newly revealed window
ACTIVE = d.intern_atom('_NET_ACTIVE_WINDOW')

ev = protocol.event.ClientMessage(
    window = new_client,
    client_type = ACTIVE,
    data = (32, [2, X.CurrentTime, 0, 0, 0])  # source=2 (pager), timestamp, requestor's window
)

root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
d.flush()

activated_title = get_window_title(d, new_client)
print(f"Activated window 0x{new_client.id:x} - {activated_title}")
