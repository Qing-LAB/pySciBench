import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backend_bases import MouseButton

t = np.arange(0.0, 1.0, 0.01)
s = np.sin(2 * np.pi * t)
fig, ax = plt.subplots()
ax.plot(t, s, picker=True)


def on_move(event):
    return
    if event.inaxes:
        print(
            f"data coords {event.xdata} {event.ydata},",
            f"pixel coords {event.x} {event.y}",
        )
    else:
        print(f"event is: ", event)


def on_click(event):
    return
    if event.button is MouseButton.LEFT:
        print("disconnecting callback")
        plt.disconnect(binding_id)


binding_id = plt.connect("motion_notify_event", on_move)
plt.connect("button_press_event", on_click)
for label in plt.gca().get_xticklabels():
    label.set_picker(True)

for label in plt.gca().get_yticklabels():
    label.set_picker(True)

plt.gca().set_picker(True)


def onpick1(event):
    prop = plt.getp(event.artist)
    print(prop)


fig.canvas.mpl_connect("pick_event", onpick1)
plt.show()

def on_close(event):
    print('Closed Figure!')

fig = plt.figure()
fig.canvas.mpl_connect('close_event', on_close)
plt.text(0.35, 0.5, 'Close Me!', dict(size=30))
plt.show()
plt.close(fig) # This will trigger the event