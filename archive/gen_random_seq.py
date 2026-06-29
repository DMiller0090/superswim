"""gen_random_seq.py - generate random superswim input sequences (sx,sy,csx,csy) for
generalization testing of the complicated predictor. Three modes:
  charge   : alternating full-deflection charge (sy 255/0) with random sx + fully random C-stick
  fullsx   : random sx across the full range (off-axis everywhere), random sy (charge-ish), random C
  chaos    : pure random everything (sx,sy,csx,csy all 0..255)
Usage: python gen_random_seq.py <mode> <nframes> <seed> > seqfile.txt   (csv: sx,sy,csx,csy)"""
import sys, random

mode = sys.argv[1] if len(sys.argv) > 1 else "charge"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 48
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
rng = random.Random(seed)

for i in range(n):
    if mode == "charge":
        sx = rng.randint(98, 158); sy = 255 if i % 2 == 0 else 0
    elif mode == "fullsx":
        sx = rng.randint(0, 255); sy = 255 if i % 2 == 0 else 0
    elif mode == "chaos":
        sx = rng.randint(0, 255); sy = rng.randint(0, 255)
    else:
        raise SystemExit("mode: charge|fullsx|chaos")
    csx = rng.randint(0, 255); csy = rng.randint(0, 255)
    print(f"{sx},{sy},{csx},{csy}")
