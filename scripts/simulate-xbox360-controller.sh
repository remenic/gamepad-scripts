#!/usr/bin/env bash

if [ -z "$1" ]; then
	echo "Usage: $0 /dev/input/eventX"

	exit 1;
fi

xboxdrv \
  --evdev $1 \
  --evdev-absmap ABS_HAT0X=dpad_x,ABS_HAT0Y=dpad_y,ABS_X=X1,ABS_Y=Y1,ABS_RX=X2,ABS_RY=Y2,ABS_Z=LT,ABS_RZ=RT \
  --evdev-keymap BTN_SOUTH=A,BTN_EAST=B,BTN_NORTH=Y,BTN_WEST=X,BTN_START=start,BTN_MODE=guide,BTN_SELECT=back \
  --evdev-keymap BTN_TL=LB,BTN_TR=RB,BTN_TL2=LT,BTN_TR2=RT,BTN_THUMBL=TL,BTN_THUMBR=TR \
  --axismap -y1=y1,-y2=y2 \
  --force-feedback \
  --mimic-xpad \
  --silent
