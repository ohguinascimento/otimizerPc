import { useEffect, useState } from 'react';

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

function getDesktopApi() {
  return window.otimizerPC;
}

function statusText(memoryUpgrade) {
  if (!memoryUpgrade) {
    return 'Análise indisponível';
  }
  if (memoryUpgrade.can_upgrade === true) {
    return 'Upgrade possível';
  }
  if (memoryUpgrade.can_upgrade === false) {
    return 'Sem upgrade óbvio';
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

export default function App() {
  const [snapshot, setSnapshot] = useState(null);
  const [processes, setProcesses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [cleanupState, setCleanupState] = useState({ status: 'idle', message: '' });

  async function loadData() {
    setError('');
    setRefreshing(true);
    try {
      const api = getDesktopApi();
      if (!api) {
        throw new Error('A API local do desktop não está disponível.');
      }

      const [snapshotData, processesData] = await Promise.all([
        api.getSnapshot(),
        api.getProcesses(8),
      ]);
      setSnapshot(snapshotData);
      setProcesses(processesData.processes || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro inesperado ao carregar os dados.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleCleanup() {
    if (!window.confirm('Confirma limpar os temporários do usuário?')) {
      return;
    }

    setCleanupState({ status: 'running', message: 'Executando limpeza segura...' });
    try {
      const api = getDesktopApi();
      if (!api) {
        throw new Error('A API local do desktop não está disponível.');
      }

      const data = await api.cleanup(true);

      setCleanupState({
        status: 'success',
        message: `Limpeza concluída. ${data.result.deleted_files} arquivos e ${data.result.deleted_folders} pastas removidos.`,
      });
      await loadData();
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

  return (
    <main className="shell">
      <div className="bg-orb bg-orb-left" />
      <div className="bg-orb bg-orb-right" />

      <header className="hero">
        <div className="hero-copy">
          <div className="eyebrow">Diagnóstico visual do Windows</div>
          <h1>Otimizer PC</h1>
          <p>
            Um painel bonito e direto para visualizar hardware, memória, processos e ações
            seguras de limpeza.
          </p>
        </div>

        <div className="hero-actions">
          <button className="btn btn-ghost" onClick={loadData} disabled={refreshing}>
            {refreshing ? 'Atualizando...' : 'Atualizar'}
          </button>
          <button className="btn btn-primary" onClick={handleCleanup} disabled={!snapshot}>
            Limpar temporários
          </button>
        </div>
      </header>

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
              ? `${snapshot.cpu_cores_physical || 'n/d'} físicos / ${snapshot.cpu_cores_logical || 'n/d'} lógicos`
              : 'Carregando...'
          }
          hint="Núcleos e threads detectados"
          tone="accent"
        />
        <MetricCard
          label="RAM"
          value={
            snapshot?.memory_total_gb != null
              ? `${formatNumber(snapshot.memory_used_gb)} / ${formatNumber(snapshot.memory_total_gb)} GB`
              : 'n/d'
          }
          hint={snapshot?.memory_percent != null ? `${formatPercent(snapshot.memory_percent)} em uso` : 'Uso de memória'}
          tone="accent"
        />
        <MetricCard
          label="Upgrade"
          value={statusText(memoryUpgrade)}
          hint={memoryUpgrade?.free_slots != null ? `${memoryUpgrade.free_slots} slots livres` : 'Slots ainda não detectados'}
          tone={statusTone(memoryUpgrade)}
        />
      </section>

      <section className="content-grid">
        <Section
          title="Resumo do hardware"
          subtitle="Placa-mãe, armazenamento e capacidade instalada."
          actions={<span className="mini-pill">{snapshot?.storage_type || 'Armazenamento n/d'}</span>}
        >
          <div className="detail-grid">
            <article className="detail-card">
              <span className="detail-label">Placa-mãe</span>
              <strong className="detail-value">
                {motherboard ? [motherboard.manufacturer, motherboard.model].filter(Boolean).join(' ') : 'Indisponível'}
              </strong>
              <span className="detail-meta">
                {motherboard?.serial_number ? `Serial: ${motherboard.serial_number}` : 'Fabricante e modelo detectados pelo sistema.'}
              </span>
            </article>

            <article className="detail-card">
              <span className="detail-label">Slots de memória</span>
              <strong className="detail-value">
                {memoryUpgrade?.used_slots != null
                  ? `${memoryUpgrade.used_slots} usados de ${memoryUpgrade.total_slots ?? 'n/d'}`
                  : 'Indisponível'}
              </strong>
              <span className="detail-meta">
                {memoryUpgrade?.free_slots != null ? `${memoryUpgrade.free_slots} livres agora` : 'A análise depende da placa e do Windows.'}
              </span>
            </article>

            <article className="detail-card highlight">
              <span className="detail-label">Conclusão de upgrade</span>
              <strong className="detail-value">
                {memoryUpgrade?.can_upgrade === true
                  ? 'Sim, há margem para upgrade'
                  : memoryUpgrade?.can_upgrade === false
                    ? 'Não há evidência clara de espaço'
                    : 'Não foi possível concluir'}
              </strong>
              <span className="detail-meta">
                {memoryUpgrade?.max_supported_gb != null
                  ? `Limite estimado da placa-mãe: ${formatNumber(memoryUpgrade.max_supported_gb)} GB`
                  : 'O limite máximo pode não ser exposto pelo firmware.'}
              </span>
            </article>
          </div>
        </Section>

        <Section
          title="Processos mais pesados"
          subtitle="Monitoramento dos processos mais consumindo memória no momento."
          actions={<span className="mini-pill">{processes.length} itens</span>}
        >
          <div className="process-list">
            {processes.length > 0 ? (
              processes.map((process) => (
                <ProcessRow key={`${process.pid}-${process.name}`} item={process} maxMemory={maxProcessMemory} />
              ))
            ) : (
              <div className="empty-state">Nenhum processo disponível no momento.</div>
            )}
          </div>
        </Section>
      </section>

      <section className="footer-grid">
        <article className="panel panel-compact">
          <div className="panel-head">
            <div>
              <h2>Disco e sistema</h2>
              <p>Leitura resumida do Windows, disco principal e pasta temporária.</p>
            </div>
          </div>

          <div className="inline-metrics">
            <div>
              <span className="inline-label">Disco do sistema</span>
              <strong>{snapshot?.system_drive ? `${snapshot.system_drive}\\` : 'n/d'}</strong>
            </div>
            <div>
              <span className="inline-label">Tipo de armazenamento</span>
              <strong>
                {snapshot?.storage_type
                  ? snapshot.storage_model
                    ? `${snapshot.storage_type} (${snapshot.storage_model})`
                    : snapshot.storage_type
                  : 'Desconhecido'}
              </strong>
            </div>
            <div>
              <span className="inline-label">Temp</span>
              <strong>{snapshot?.temp_dir || 'n/d'}</strong>
            </div>
          </div>
        </article>

        <article className="panel panel-compact panel-callout">
          <div className={`callout callout-${statusTone(memoryUpgrade)}`}>
            <span className="callout-label">Status da RAM</span>
            <strong>{statusText(memoryUpgrade)}</strong>
            <p>
              {memoryUpgrade
                ? `RAM instalada: ${formatNumber(memoryUpgrade.installed_gb)} GB. ` +
                  `Slots livres: ${formatNumber(memoryUpgrade.free_slots)}.`
                : 'A análise de memória pode variar conforme o suporte exposto pela placa-mãe.'}
            </p>
          </div>
        </article>
      </section>
    </main>
  );
}
