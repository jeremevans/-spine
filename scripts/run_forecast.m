function run_forecast(input_path, output_path)
% Independent centered PCA/SVD + intercept OLS AR(1), no Statistics Toolbox.
% Inputs are already aligned log-IV. Interpolation has a separate verifier.
f = jsondecode(fileread(input_path));
if exist('OCTAVE_VERSION', 'builtin')
    engine = 'Octave'; engine_version = OCTAVE_VERSION;
else
    engine = 'MATLAB'; engine_version = version;
end
rows = cell(numel(f.payload.cases), 1);
for i = 1:numel(rows)
    c = f.payload.cases(i); X = c.train_log; k = c.k;
    mu = mean(X, 1); Z = X - mu;
    [~, S, V] = svd(Z, 'econ'); L = V(:, 1:k); scores = Z * L;
    adjacent = diff(c.months(:)) == 1;
    phi = zeros(k,1); predicted = zeros(k,1);
    for j = 1:k
        lag = scores(1:end-1,j); lead = scores(2:end,j);
        B = [ones(sum(adjacent),1), lag(adjacent)] \ lead(adjacent);
        phi(j) = B(2); predicted(j) = B(1) + B(2)*scores(end,j);
    end
    eigenvalues = diag(S).^2;
    rows{i} = struct('name',c.name,'forecast_log',mu(:)+L*predicted, ...
        'projector',L*L','phi',phi,'explained_ratio',eigenvalues(1:k)/sum(eigenvalues));
end
out = struct('engine',engine,'engine_version',engine_version, ...
    'fixture_id',f.fixture_id,'cases',{rows});
fid = fopen(output_path,'w');
if fid < 0, error('Cannot open output'); end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid,'%s\n',jsonencode(out));
end
