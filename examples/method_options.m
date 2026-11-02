% Run from the repository root in MATLAB or Octave.
addpath('matlab');m=[.8,.95,1.05,1.2];t=[.1,.5,1,2];
[M,T]=ndgrid(m,t);iv=.2+.15*(M-1).^2+.04*exp(-T);
q=[.9,.3;1,.75;1.1,1.5];
for method={'spline','linear','nadaraya_watson'}
  h=[];if strcmp(method{1},'nadaraya_watson'),h=[.08,.3];end
  fitted=interpolate_surface({m,t},iv,q,method{1},h,NaN);
  assert(all(isfinite(fitted)) && all(fitted>0));
  disp(method{1});disp([fitted,log(fitted)]);
end
