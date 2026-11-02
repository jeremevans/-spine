function y = interpolate_surface(axes, values, q, method, bandwidth, fill)
% Select native spline/linear interpolation or explicit Gaussian NW regression.
% Grid values use MATLAB column-major order. Queries are rows of paired points.
  if nargin<4, method='spline'; end
  if nargin<5, bandwidth=[]; end
  if nargin<6, fill=NaN; end
  assert(any(strcmp(method,{'spline','linear','nadaraya_watson'})));
  assert(isscalar(fill) && isreal(fill));
  d=numel(axes); assert(d>0 && iscell(axes) && ismatrix(q) && size(q,2)==d);
  assert(isreal(values) && isreal(q) && all(isfinite(values(:))) && all(isfinite(q(:))));
  shape=cellfun(@numel,axes); assert(numel(values)==prod(shape));
  minimum=2; if strcmp(method,'spline'), minimum=4; end
  inside=true(size(q,1),1);
  for j=1:d
    x=axes{j}; assert(isvector(x) && isreal(x) && numel(x)>=minimum && ...
                     all(isfinite(x(:))) && all(diff(x(:))>0));
    inside=inside & q(:,j)>=x(1) & q(:,j)<=x(end);
  end
  if strcmp(method,'nadaraya_watson')
    if isempty(bandwidth), error('nadaraya_watson requires explicit bandwidths'); end
    g=cell(1,d); [g{:}]=ndgrid(axes{:}); points=zeros(numel(values),d);
    for j=1:d, points(:,j)=g{j}(:); end
    y=repmat(fill,size(q,1),1);
    y(inside)=nadaraya_watson(points,values(:),q(inside,:),bandwidth);
  else
    if ~isempty(bandwidth), error('bandwidth applies only to nadaraya_watson'); end
    if d==1, y=interp1(axes{1},values(:),q(:,1),method,fill); return; end
    values=reshape(values,shape); y=zeros(size(q,1),1);
    args=cell(1,d);
    % Scalar calls avoid differences in paired-vector query semantics.
    for i=1:size(q,1)
      for j=1:d, args{j}=q(i,j); end
      y(i)=interpn(axes{:},values,args{:},method,fill);
    end
  end
end
