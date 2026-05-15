import { useEffect, useMemo, useState } from 'react';

const numberFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 1,
});

function formatNumber(value) {
  if (value === null || value === undefined) {
    return 'n/d';
  }
  return numberFormatter.format(value);
}

function formatPercent(value) {
  if (value === null || value === undefined) {
    return 'n/d';
  }
  return `${numberFormatter.format(value)}%`;
}

function formatAddress(host, port) {
  if (!host && host !== '') {
    return 'n/d';
  }
  if (!port && port !== 0) {
    return host || 'n/d';
  }
  return `${host}:${port}`;
}

function truncateMiddle(value, limit = 60) {
  if (!value || value.length <= limit) {
    return value || 'n/d';
  }
  if (limit <= 3) {
    return '...';
  }
  const head = Math.max(1, Math.floor((limit - 3) / 2));
  const tail = Math.max(1, limit - 3 - head);
  return `${value.slice(0, head)}...${value.slice(-tail)}`;
}

function getDesktopApi() {
  return window.otimizerPC || null;
}

function statusText(memoryUpgrade) {
  if (!memoryUpgrade) {
    return 'Analise indisponivel';
  }
  if (memoryUpgrade.can_upgrade === true) {
    return 'Upgrade possivel';
  }
  if (memoryUpgrade.can_upgrade === false) {
    return 'Sem upgrade obvio';
  }
  return 'Dados insuficientes';
}

function statusTone(memoryUpgrade) {
  if (!memoryUpgrade) {
    return 'muted';
  }
  if (memoryUpgrade.can_upgrade === true) {
    return 'success';
  }
  if (memoryUpgrade.can_upgrade === false) {
    return 'warning';
  }
  return 'muted';
}

function riskLabel(value) {
  if (value === 'alto') {
    return 'Alto';
  }
  if (value === 'medio') {
    return 'Medio';
  }
  return 'Baixo';
}

function riskTone(value) {
  if (value === 'alto') {
    return 'danger';
  }
  if (value === 'medio') {
    return 'warning';
  }
  return 'success';
}

function fileCategory(extension) {
  const ext = (extension || '').toLowerCase();
  if (['.exe', '.dll', '.sys', '.scr', '.com', '.msi', '.msp'].includes(ext)) {
    return 'executavel';
  }
  if (['.ps1', '.bat', '.cmd', '.vbs', '.js', '.jse'].includes(ext)) {
    return 'script';
  }
  if (['.lnk', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.rtf'].includes(ext)) {
    return 'documento';
  }
  return 'outro';
}

function fileCategoryLabel(value) {
  if (value === 'executavel') {
    return 'Executavel';
  }
  if (value === 'script') {
    return 'Script';
  }
  if (value === 'documento') {
    return 'Documento';
  }
  return 'Outro';
}

function MetricCard({ label, value, hint, tone = 'neutral' }) {
  return (
    <article className={`metric-card metric-${tone}`}>
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
      {hint ? <span className="metric-hint">{hint}</span> : null}
    </article>
  );
}

function ProcessRow({ item, maxMemory }) {
  const share = maxMemory > 0 ? (item.memory_mb / maxMemory) * 100 : 0;

  return (
    <div className="process-row">
      <div className="process-main">
        <div className="process-name">{item.name}</div>
        <div className="process-meta">PID {item.pid}</div>
      </div>
      <div className="process-details">
        <div className="process-numbers">
          <span>{formatPercent(item.cpu_percent)} CPU</span>
          <span>{formatNumber(item.memory_mb)} MB</span>
        </div>
        <div className="memory-bar">
          <span style={{ width: `${Math.max(6, share)}%` }} />
        </div>
      </div>
    </div>
  );
}

function NetworkRow({ item }) {
  const reasons = item.risk_reasons?.length ? item.risk_reasons.join(', ') : 'Sem alertas adicionais';

  return (
    <div className="network-row">
      <div className="network-main">
        <div className="network-topline">
          <strong>{item.process_name}</strong>
          <span className={`risk-badge risk-${riskTone(item.risk_level)}`}>{riskLabel(item.risk_level)}</span>
        </div>
        <div className="network-meta">
          <span>PID {item.pid ?? 'n/d'}</span>
          <span>{item.protocol.toUpperCase()}</span>
          <span>{item.status}</span>
        </div>
        <div className="network-path">
          <span>Local: {formatAddress(item.local_address, item.local_port)}</span>
          <span>Remoto: {item.remote_address ? formatAddress(item.remote_address, item.remote_port) : 'n/d'}</span>
        </div>
      </div>
      <div className="network-side">
        <span className="network-path-label">Arquivo</span>
        <strong>{item.exe_path || 'n/d'}</strong>
        <span className="network-path-label">Usuario</span>
        <strong>{item.username || 'n/d'}</strong>
        <span className="network-path-label">Motivos</span>
        <p>{reasons}</p>
      </div>
    </div>
  );
}

function FileRow({ item }) {
  const reasons = item.risk_reasons?.length ? item.risk_reasons.join(', ') : 'Sem alertas adicionais';
  const category = fileCategory(item.extension);

  return (
    <div className="file-row">
      <div className="file-main">
        <div className="network-topline">
          <strong>{item.name}</strong>
          <span className={`risk-badge risk-${riskTone(item.risk_level)}`}>{riskLabel(item.risk_level)}</span>
        </div>
        <div className="network-meta">
          <span>{fileCategoryLabel(category)}</span>
          <span>{item.extension || 'sem extensao'}</span>
          <span>{item.risk_score} pontos</span>
        </div>
        <div className="network-path">
          <span>{item.path}</span>
        </div>
      </div>
      <div className="network-side">
        <span className="network-path-label">Modificado</span>
        <strong>{item.modified_at || 'n/d'}</strong>
        <span className="network-path-label">Criado</span>
        <strong>{item.created_at || 'n/d'}</strong>
        <span className="network-path-label">Motivos</span>
        <p>{reasons}</p>
      </div>
    </div>
  );
}

function Section({ title, subtitle, children, actions }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {actions ? <div className="panel-actions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

function TabButton({ active, onClick, children }) {
  return (
    <button className={`tab-button ${active ? 'active' : ''}`} onClick={onClick} type="button">
      {children}
    </button>
  );
}

export default function App() {
  const [snapshot, setSnapshot] = useState(null);
  const [processes, setProcesses] = useState([]);
  const [networkAudit, setNetworkAudit] = useState(null);
  const [fileAudit, setFileAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [fileLoading, setFileLoading] = useState(false);
  const [error, setError] = useState('');
  const [cleanupState, setCleanupState] = useState({ status: 'idle', message: '' });
  const [activeTab, setActiveTab] = useState('overview');
  const [networkSearch, setNetworkSearch] = useState('');
  const [networkRiskFilter, setNetworkRiskFilter] = useState('all');
  const [networkStatusFilter, setNetworkStatusFilter] = useState('all');
  const [networkProtocolFilter, setNetworkProtocolFilter] = useState('all');
  const [networkScopeFilter, setNetworkScopeFilter] = useState('all');
  const [fileSearch, setFileSearch] = useState('');
  const [fileRiskFilter, setFileRiskFilter] = useState('all');
  const [fileCategoryFilter, setFileCategoryFilter] = useState('all');
  const [fileRecentOnly, setFileRecentOnly] = useState(true);

  const apiAvailable = useMemo(() => Boolean(getDesktopApi()), []);

  async function loadCoreData() {
    setError('');
    setRefreshing(true);
    try {
      const api = getDesktopApi();
      if (!api) {
        throw new Error('A API local do desktop nao esta disponivel.');
      }

      const [snapshotData, processesData, networkData] = await Promise.all([
        api.getSnapshot(),
        api.getProcesses(8),
        api.getNetworkAudit(25),
      ]);

      setSnapshot(snapshotData);
      setProcesses(processesData.processes || []);
      setNetworkAudit(networkData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro inesperado ao carregar os dados.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  async function loadFileAudit() {
    if (fileLoading || fileAudit) {
      return;
    }

    setError('');
    setFileLoading(true);
    try {
      const api = getDesktopApi();
      if (!api) {
        throw new Error('A API local do desktop nao esta disponivel.');
      }

      const fileData = await api.getFileAudit(40, 7);
      setFileAudit(fileData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro inesperado ao carregar a auditoria de arquivos.');
    } finally {
      setFileLoading(false);
    }
  }

  useEffect(() => {
    loadCoreData();
  }, []);

  useEffect(() => {
    if (activeTab === 'files' && !fileAudit && !fileLoading && apiAvailable) {
      loadFileAudit();
    }
  }, [activeTab, fileAudit, fileLoading, apiAvailable]);

  async function handleCleanup() {
    if (!window.confirm('Confirma limpar os temporarios do usuario?')) {
      return;
    }

    setCleanupState({ status: 'running', message: 'Executando limpeza segura...' });
    try {
      const api = getDesktopApi();
      if (!api) {
        throw new Error('A API local do desktop nao esta disponivel.');
      }

      const data = await api.cleanup(true);

      setCleanupState({
        status: 'success',
        message: `Limpeza concluida. ${data.result.deleted_files} arquivos e ${data.result.deleted_folders} pastas removidos.`,
      });
      await loadCoreData();
      if (activeTab === 'files') {
        await loadFileAudit();
      }
    } catch (err) {
      setCleanupState({
        status: 'error',
        message: err instanceof Error ? err.message : 'Erro inesperado na limpeza.',
      });
    }
  }

  const motherboard = snapshot?.motherboard || null;
  const memoryUpgrade = snapshot?.memory_upgrade || null;
  const maxProcessMemory = Math.max(...processes.map((item) => item.memory_mb), 1);
  const networkConnections = networkAudit?.connections || [];
  const fileEntries = fileAudit?.entries || [];
  const filteredNetworkConnections = useMemo(() => {
    const query = networkSearch.trim().toLowerCase();

    return networkConnections.filter((item) => {
      if (networkRiskFilter !== 'all' && item.risk_level !== networkRiskFilter) {
        return false;
      }

      if (networkStatusFilter !== 'all' && item.status !== networkStatusFilter) {
        return false;
      }

      if (networkProtocolFilter !== 'all' && item.protocol !== networkProtocolFilter) {
        return false;
      }

      if (networkScopeFilter === 'remote' && !item.remote_address) {
        return false;
      }

      if (networkScopeFilter === 'listening' && item.status !== 'LISTEN') {
        return false;
      }

      if (!query) {
        return true;
      }

      const haystack = [
        item.process_name,
        item.exe_path,
        item.username,
        item.protocol,
        item.status,
        item.local_address,
        item.remote_address,
        String(item.pid ?? ''),
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return haystack.includes(query);
    });
  }, [networkConnections, networkSearch, networkRiskFilter, networkStatusFilter, networkProtocolFilter, networkScopeFilter]);

  const filteredFileEntries = useMemo(() => {
    const query = fileSearch.trim().toLowerCase();

    return fileEntries.filter((item) => {
      if (fileRiskFilter !== 'all' && item.risk_level !== fileRiskFilter) {
        return false;
      }

      const category = fileCategory(item.extension);
      if (fileCategoryFilter !== 'all' && category !== fileCategoryFilter) {
        return false;
      }

      if (fileRecentOnly && item.risk_reasons && !item.risk_reasons.includes('modificado recentemente') && !item.risk_reasons.includes('modificado nas ultimas 24h')) {
        return false;
      }

      if (!query) {
        return true;
      }

      const haystack = [
        item.name,
        item.path,
        item.extension,
        item.modified_at,
        item.created_at,
        item.accessed_at,
        String(item.risk_score ?? ''),
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return haystack.includes(query);
    });
  }, [fileEntries, fileSearch, fileRiskFilter, fileCategoryFilter, fileRecentOnly]);

  function resetNetworkFilters() {
    setNetworkSearch('');
    setNetworkRiskFilter('all');
    setNetworkStatusFilter('all');
    setNetworkProtocolFilter('all');
    setNetworkScopeFilter('all');
  }

  function resetFileFilters() {
    setFileSearch('');
    setFileRiskFilter('all');
    setFileCategoryFilter('all');
    setFileRecentOnly(true);
  }

  return (
    <main className="shell">
      <div className="bg-orb bg-orb-left" />
      <div className="bg-orb bg-orb-right" />

      <header className="hero">
        <div className="hero-copy">
          <div className="eyebrow">Diagnostico visual do Windows</div>
          <h1>Otimizer PC</h1>
          <p>
            Um painel bonito e direto para visualizar hardware, rede, processos e acoes
            seguras de limpeza.
          </p>
        </div>

        <div className="hero-actions">
          <button
            className="btn btn-ghost"
            onClick={() => {
              loadCoreData();
              if (activeTab === 'files') {
                loadFileAudit();
              }
            }}
            disabled={refreshing || fileLoading}
          >
            {refreshing ? 'Atualizando...' : 'Atualizar'}
          </button>
          <button className="btn btn-primary" onClick={handleCleanup} disabled={!snapshot}>
            Limpar temporarios
          </button>
        </div>
      </header>

      {!apiAvailable ? <div className="alert alert-error">A API local do desktop nao foi carregada.</div> : null}
      {error ? <div className="alert alert-error">{error}</div> : null}
      {cleanupState.status !== 'idle' ? (
        <div className={`alert alert-${cleanupState.status}`}>{cleanupState.message}</div>
      ) : null}

      <section className="stats-grid">
        <MetricCard
          label="Sistema"
          value={snapshot ? `${snapshot.os_name} ${snapshot.os_release}` : loading ? 'Carregando...' : 'n/d'}
          hint={snapshot ? snapshot.architecture : 'Arquitetura do sistema'}
          tone="neutral"
        />
        <MetricCard
          label="CPU"
          value={
            snapshot
              ? `${snapshot.cpu_cores_physical || 'n/d'} fisicos / ${snapshot.cpu_cores_logical || 'n/d'} logicos`
              : 'Carregando...'
          }
          hint="Nucleos e threads detectados"
          tone="accent"
        />
        <MetricCard
          label="RAM"
          value={
            snapshot?.memory_total_gb != null
              ? `${formatNumber(snapshot.memory_used_gb)} / ${formatNumber(snapshot.memory_total_gb)} GB`
              : 'n/d'
          }
          hint={snapshot?.memory_percent != null ? `${formatPercent(snapshot.memory_percent)} em uso` : 'Uso de memoria'}
          tone="accent"
        />
        <MetricCard
          label="Rede"
          value={networkAudit ? `${networkAudit.total_connections} conexoes` : 'n/d'}
          hint={networkAudit ? `${networkAudit.suspicious_connections} marcadas` : 'Auditoria de rede'}
          tone={networkAudit?.suspicious_connections > 0 ? 'warning' : 'neutral'}
        />
      </section>

      <section className="tab-bar">
        <TabButton active={activeTab === 'overview'} onClick={() => setActiveTab('overview')}>
          Visao geral
        </TabButton>
        <TabButton active={activeTab === 'network'} onClick={() => setActiveTab('network')}>
          Auditoria de rede
        </TabButton>
        <TabButton active={activeTab === 'files'} onClick={() => setActiveTab('files')}>
          Arquivos
        </TabButton>
        <TabButton active={activeTab === 'processes'} onClick={() => setActiveTab('processes')}>
          Processos
        </TabButton>
        <TabButton active={activeTab === 'cleanup'} onClick={() => setActiveTab('cleanup')}>
          Limpeza
        </TabButton>
      </section>

      {activeTab === 'overview' ? (
        <section className="content-grid">
          <Section
            title="Resumo do hardware"
            subtitle="Placa-mae, armazenamento e capacidade instalada."
            actions={<span className="mini-pill">{snapshot?.storage_type || 'Armazenamento n/d'}</span>}
          >
            <div className="detail-grid">
              <article className="detail-card">
                <span className="detail-label">Placa-mae</span>
                <strong className="detail-value">
                  {motherboard ? [motherboard.manufacturer, motherboard.model].filter(Boolean).join(' ') : 'Indisponivel'}
                </strong>
                <span className="detail-meta">
                  {motherboard?.serial_number ? `Serial: ${motherboard.serial_number}` : 'Fabricante e modelo detectados pelo sistema.'}
                </span>
              </article>

              <article className="detail-card">
                <span className="detail-label">Slots de memoria</span>
                <strong className="detail-value">
                  {memoryUpgrade?.used_slots != null
                    ? `${memoryUpgrade.used_slots} usados de ${memoryUpgrade.total_slots ?? 'n/d'}`
                    : 'Indisponivel'}
                </strong>
                <span className="detail-meta">
                  {memoryUpgrade?.free_slots != null ? `${memoryUpgrade.free_slots} livres agora` : 'A analise depende da placa e do Windows.'}
                </span>
              </article>

              <article className="detail-card highlight">
                <span className="detail-label">Conclusao de upgrade</span>
                <strong className="detail-value">
                  {memoryUpgrade?.can_upgrade === true
                    ? 'Sim, ha margem para upgrade'
                    : memoryUpgrade?.can_upgrade === false
                      ? 'Nao ha evidencia clara de espaco'
                      : 'Nao foi possivel concluir'}
                </strong>
                <span className="detail-meta">
                  {memoryUpgrade?.max_supported_gb != null
                    ? `Limite estimado da placa-mae: ${formatNumber(memoryUpgrade.max_supported_gb)} GB`
                    : 'O limite maximo pode nao ser exposto pelo firmware.'}
                </span>
              </article>
            </div>
          </Section>

          <Section
            title="Disco e sistema"
            subtitle="Leitura resumida do Windows, disco principal e pasta temporaria."
            actions={<span className="mini-pill">{snapshot?.system_drive || 'n/d'}</span>}
          >
            <div className="detail-grid">
              <article className="detail-card">
                <span className="detail-label">Disco do sistema</span>
                <strong className="detail-value">{snapshot?.system_drive ? `${snapshot.system_drive}\\` : 'n/d'}</strong>
                <span className="detail-meta">
                  {snapshot?.storage_model ? snapshot.storage_model : 'Dispositivo principal detectado pelo Windows.'}
                </span>
              </article>

              <article className="detail-card">
                <span className="detail-label">Temp</span>
                <strong className="detail-value detail-value-ellipsis" title={snapshot?.temp_dir || 'n/d'}>
                  {truncateMiddle(snapshot?.temp_dir, 64)}
                </strong>
                <span className="detail-meta">Pasta usada nas rotinas de limpeza segura.</span>
              </article>

              <article className="detail-card">
                <span className="detail-label">Status da RAM</span>
                <strong className="detail-value">{statusText(memoryUpgrade)}</strong>
                <span className="detail-meta">
                  {memoryUpgrade?.installed_gb != null
                    ? `RAM instalada: ${formatNumber(memoryUpgrade.installed_gb)} GB`
                    : 'Analise dependente do suporte exposto pela placa-mae.'}
                </span>
              </article>
            </div>
          </Section>
        </section>
      ) : null}

      {activeTab === 'network' ? (
        <section className="content-grid">
          <Section
            title="Auditoria de rede"
            subtitle="Conexoes ativas, portas escutando e sinais que merecem investigacao."
            actions={<span className="mini-pill">{networkAudit?.status || 'n/d'}</span>}
          >
            {networkAudit?.warning ? <div className="section-warning">{networkAudit.warning}</div> : null}
            <div className="audit-grid">
              <MetricCard label="Total" value={networkAudit ? networkAudit.total_connections : 'n/d'} hint="Conexoes IPv4/IPv6" tone="neutral" />
              <MetricCard label="Estabelecidas" value={networkAudit ? networkAudit.established_connections : 'n/d'} hint="Sessao ativa agora" tone="accent" />
              <MetricCard label="Escutando" value={networkAudit ? networkAudit.listening_connections : 'n/d'} hint="Portas abertas" tone="accent" />
              <MetricCard label="Suspeitas" value={networkAudit ? networkAudit.suspicious_connections : 'n/d'} hint="Marcadas pelas regras" tone={networkAudit?.suspicious_connections > 0 ? 'warning' : 'success'} />
            </div>
            <div className="network-filters">
              <input
                className="network-search"
                value={networkSearch}
                onChange={(event) => setNetworkSearch(event.target.value)}
                placeholder="Filtrar por processo, IP, PID, caminho..."
              />

              <select className="network-select" value={networkRiskFilter} onChange={(event) => setNetworkRiskFilter(event.target.value)}>
                <option value="all">Todos os riscos</option>
                <option value="alto">Alto risco</option>
                <option value="medio">Médio risco</option>
                <option value="baixo">Baixo risco</option>
              </select>

              <select className="network-select" value={networkStatusFilter} onChange={(event) => setNetworkStatusFilter(event.target.value)}>
                <option value="all">Todos os status</option>
                <option value="ESTABLISHED">ESTABLISHED</option>
                <option value="LISTEN">LISTEN</option>
                <option value="CLOSE_WAIT">CLOSE_WAIT</option>
                <option value="TIME_WAIT">TIME_WAIT</option>
                <option value="NONE">NONE</option>
              </select>

              <select className="network-select" value={networkProtocolFilter} onChange={(event) => setNetworkProtocolFilter(event.target.value)}>
                <option value="all">Todos os protocolos</option>
                <option value="tcp">TCP</option>
                <option value="udp">UDP</option>
                <option value="unknown">Unknown</option>
              </select>

              <select className="network-select" value={networkScopeFilter} onChange={(event) => setNetworkScopeFilter(event.target.value)}>
                <option value="all">Escopo completo</option>
                <option value="remote">Somente remoto</option>
                <option value="listening">Somente escutando</option>
              </select>

              <button className="btn btn-ghost network-reset" type="button" onClick={resetNetworkFilters}>
                Limpar filtros
              </button>
            </div>
            <div className="network-filter-summary">
              Exibindo {filteredNetworkConnections.length} de {networkConnections.length} conexões carregadas
            </div>
            <div className="network-list">
              {filteredNetworkConnections.length > 0 ? (
                filteredNetworkConnections.map((item, index) => <NetworkRow key={`${item.pid || 'x'}-${item.process_name}-${index}`} item={item} />)
              ) : (
                <div className="empty-state">Nenhuma conexão encontrada com os filtros atuais.</div>
              )}
            </div>
          </Section>
        </section>
      ) : null}

      {activeTab === 'files' ? (
        <section className="content-grid">
          <Section
            title="Analise de modificacoes"
            subtitle="Arquivos alterados recentemente, com foco em executaveis e scripts suspeitos."
            actions={<span className="mini-pill">{fileLoading ? 'Carregando...' : fileAudit?.backend || 'sob demanda'}</span>}
          >
            {!fileAudit && !fileLoading ? (
              <div className="section-warning">
                A leitura de arquivos foi adiada para acelerar a abertura. Abra esta aba para carregar a analise.
              </div>
            ) : null}
            {fileAudit?.warning ? <div className="section-warning">{fileAudit.warning}</div> : null}
            <div className="audit-grid">
              <MetricCard label="Total" value={fileAudit ? fileAudit.total_files : 'n/d'} hint="Arquivos varridos" tone="neutral" />
              <MetricCard
                label="Suspeitos"
                value={fileAudit ? fileAudit.suspicious_files : 'n/d'}
                hint="Marcados pela heuristica"
                tone={fileAudit?.suspicious_files > 0 ? 'warning' : 'success'}
              />
              <MetricCard label="Janela" value={fileAudit ? `${fileAudit.recent_days} dias` : 'n/d'} hint="Filtro temporal base" tone="accent" />
              <MetricCard label="Coleta" value={fileAudit ? fileAudit.backend : 'n/d'} hint="pytsk3 ou fallback local" tone="accent" />
            </div>
            <div className="network-filters">
              <input
                className="network-search"
                value={fileSearch}
                onChange={(event) => setFileSearch(event.target.value)}
                placeholder="Filtrar por nome, caminho, extensao..."
              />

              <select className="network-select" value={fileRiskFilter} onChange={(event) => setFileRiskFilter(event.target.value)}>
                <option value="all">Todos os riscos</option>
                <option value="alto">Alto risco</option>
                <option value="medio">Médio risco</option>
                <option value="baixo">Baixo risco</option>
              </select>

              <select className="network-select" value={fileCategoryFilter} onChange={(event) => setFileCategoryFilter(event.target.value)}>
                <option value="all">Todas as categorias</option>
                <option value="executavel">Executavel</option>
                <option value="script">Script</option>
                <option value="documento">Documento</option>
                <option value="outro">Outro</option>
              </select>

              <label className="toggle-chip">
                <input
                  type="checkbox"
                  checked={fileRecentOnly}
                  onChange={(event) => setFileRecentOnly(event.target.checked)}
                />
                <span>Somente recentes</span>
              </label>

              <button className="btn btn-ghost network-reset" type="button" onClick={resetFileFilters}>
                Limpar filtros
              </button>
            </div>
            <div className="network-filter-summary">
              Exibindo {filteredFileEntries.length} de {fileEntries.length} arquivos marcados
            </div>
            <div className="network-list">
              {filteredFileEntries.length > 0 ? (
                filteredFileEntries.map((item, index) => <FileRow key={`${item.path}-${index}`} item={item} />)
              ) : (
                <div className="empty-state">Nenhum arquivo encontrado com os filtros atuais.</div>
              )}
            </div>
          </Section>
        </section>
      ) : null}

      {activeTab === 'processes' ? (
        <section className="content-grid">
          <Section
            title="Processos mais pesados"
            subtitle="Monitoramento dos processos que mais consomem recursos no momento."
            actions={<span className="mini-pill">{processes.length} itens</span>}
          >
            <div className="process-list">
              {processes.length > 0 ? (
                processes.map((process) => (
                  <ProcessRow key={`${process.pid}-${process.name}`} item={process} maxMemory={maxProcessMemory} />
                ))
              ) : (
                <div className="empty-state">Nenhum processo disponivel no momento.</div>
              )}
            </div>
          </Section>
        </section>
      ) : null}

      {activeTab === 'cleanup' ? (
        <section className="content-grid">
          <Section
            title="Limpeza segura"
            subtitle="Remocao de temporarios do usuario com confirmacao explicita."
            actions={<span className="mini-pill">Acoes limitadas</span>}
          >
            <div className="detail-grid">
              <article className="detail-card highlight">
                <span className="detail-label">Escopo</span>
                <strong className="detail-value">Apenas temporarios do usuario</strong>
                <span className="detail-meta">
                  A limpeza evita processos agressivos e nao faz encerramento automatico de aplicativos.
                </span>
              </article>

              <article className="detail-card">
                <span className="detail-label">Ultimo resultado</span>
                <strong className="detail-value">
                  {cleanupState.status === 'idle' ? 'Ainda nao executada' : cleanupState.status}
                </strong>
                <span className="detail-meta">{cleanupState.message || 'Nenhuma execucao recente.'}</span>
              </article>

              <article className="detail-card">
                <span className="detail-label">Acao</span>
                <strong className="detail-value">Executar limpeza segura</strong>
                <span className="detail-meta">
                  Use o botao no topo para confirmar a remocao de arquivos temporarios.
                </span>
              </article>
            </div>
          </Section>
        </section>
      ) : null}
    </main>
  );
}
