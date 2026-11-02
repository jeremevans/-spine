"""Same paired queries, three selectable methods."""
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from spline_equivalence import interpolate_surface

m=np.array([.8,.95,1.05,1.2]);t=np.array([.1,.5,1.,2.])
M,T=np.meshgrid(m,t,indexing='ij')
iv=.2+.15*(M-1)**2+.04*np.exp(-T)
q=np.array([[.9,.3],[1.,.75],[1.1,1.5]])
for method in ['spline','linear','nadaraya_watson']:
    fitted=interpolate_surface((m,t),iv,q,method=method,
        bandwidth=[.08,.3] if method=='nadaraya_watson' else None)
    if not (np.isfinite(fitted)&(fitted>0)).all():raise ValueError('Invalid IV before log')
    print(method, 'IV:', fitted, 'log IV:', np.log(fitted))
