function y = nadaraya_watson(points, values, q, bandwidth)
% Gaussian local-constant regression. Bandwidths are coordinate standard deviations.
% Scattered points and paired queries are matrices with one observation per row.
  assert(ismatrix(points) && size(points,1)>0 && size(points,2)>0);
  d=size(points,2);
  assert(ismatrix(q) && size(q,2)==d && isvector(values) && numel(values)==size(points,1));
  assert(isreal(points) && isreal(values) && isreal(q) && isreal(bandwidth));
  assert(all(isfinite(points(:))) && all(isfinite(values(:))) && all(isfinite(q(:))));
  assert(isvector(bandwidth) && any(numel(bandwidth)==[1,d]) && ...
         all(isfinite(bandwidth(:))) && all(bandwidth(:)>0));
  h=bandwidth(:)'; if isscalar(h), h=repmat(h,1,d); end
  values=values(:); scale=max(1,max(abs(values))); y=zeros(size(q,1),1);
  for i=1:size(q,1)
    delta=bsxfun(@rdivide,bsxfun(@minus,points,q(i,:)),h);
    d2=sum(delta.*delta,2);
    if ~all(isfinite(d2)), error('Scaled distances overflow; rescale coordinates or bandwidths'); end
    lw=-.5*d2; w=exp(lw-max(lw)); w=w/sum(w);
    y(i)=sum(w.*(values/scale))*scale;
  end
end
