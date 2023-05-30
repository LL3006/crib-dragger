# CribDragger

CribDragger is a terminal editor to make crib dragging easy. 

CribDragger will display a generic ciphertext and run a function that takes in changes in plaintext and then replaces it.

Example:
```python
from crib_dragger import CribDragger, PartialString

with open("./ciphertext.txt", "r") as f:
	ciphertext = f.read()

def on_change(prev: PartialString = None, current: PartialString = None):
	if prev and current:
		for i, (x,y) in enumerate(zip(prev, current)):
			if x != y:
				if y != None:
					key.add_known(i, ciphertext[i], y)
				else:
					key.remove(i)
			
	return some_decrypt_function(ciphertext, key)

CribDragger(ciphertext, on_change).run()

```

There are still many unresolved issues at this stage but the program _should_ be fairly usable.


This project initial was thought as a fork of [this repo](https://github.com/CameronLonsdale/MTP) but eventually I figured building it from scratch would've just been easier. Still, shoutout to the original program.