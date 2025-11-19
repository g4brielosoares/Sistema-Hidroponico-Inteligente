// frontend/static/js/dashboard.js

// ======================= HELPERS DE API =======================

async function apiGet(url) {
  const resp = await fetch(url);
  const data = await resp.json().catch(() => ({}));
  return { status: resp.status, data };
}

async function apiDelete(url) {
  const resp = await fetch(url, {
    method: "DELETE",
  });
  const data = await resp.json().catch(() => ({}));
  return { status: resp.status, data };
}

/**
 * POST genérico.
 * Se asDevice = true, manda o X-API-KEY do "gateway" (dispositivo).
 */
async function apiPost(url, body = {}, { asDevice = false } = {}) {
  const headers = {
    "Content-Type": "application/json",
  };

  if (asDevice) {
    // MESMO VALOR definido em Config.DEVICE_API_KEY no backend
    headers["X-API-KEY"] = "MEU_TOKEN_DISPOSITIVO_SUPER_SECRETO";
  }

  const resp = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  let data = {};
  const contentType = resp.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    data = await resp.json().catch(() => ({}));
  }

  return { status: resp.status, data };
}

// ======================= HELPERS DE FORMATAÇÃO =======================

function formatUnidade(unidade) {
  if (!unidade) return "-";
  switch (unidade) {
    case "°C":
      return "°C (Graus Celsius)";
    case "mS/cm":
      return "mS/cm (Condutividade)";
    case "%":
      return "% (Percentual)";
    case "lux":
      return "lux (Luminosidade)";
    default:
      return unidade;
  }
}

function formatDataHora(iso) {
  if (!iso) return "-";
  try {
    const dt = new Date(iso);
    return dt.toLocaleString();
  } catch {
    return iso;
  }
}

function formatValor(v) {
  if (v === null || v === undefined || isNaN(v)) return "-";
  return Number(v).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// ======================= SENSORES =======================

async function carregarSensores() {
  const tabela = document.getElementById("tabela-sensores");
  if (!tabela) return;

  const tbody = tabela.querySelector("tbody");
  const { status, data } = await apiGet("/api/sensores");
  if (status !== 200) return;

  tbody.innerHTML = "";

  // data já vem com último primeiro do backend, mas, para garantir:
  const sensores = data.slice();

  sensores.forEach((s) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${s.id}</td>
      <td>${s.tipo}</td>
      <td>${formatUnidade(s.unidade)}</td>
      <td>${s.modelo || "-"}</td>
      <td>${s.localizacao || "-"}</td>
    `;
    tbody.appendChild(tr);
  });
}

function initSensoresPage() {
  const form = document.getElementById("form-sensor");
  const tabela = document.getElementById("tabela-sensores");
  if (!form || !tabela) return; // não está na página de sensores

  const statusSpan = document.getElementById("status-sensor");
  const btnLimpar = document.getElementById("btn-limpar-sensores");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const id = document.getElementById("sensorId").value.trim();
    const tipo = document.getElementById("sensorTipo").value;
    const modelo = document.getElementById("sensorModelo").value.trim();
    const localizacao = document.getElementById("sensorLocal").value.trim();

    if (!id || !tipo) {
      if (statusSpan) {
        statusSpan.textContent = "Preencha ID e tipo.";
        statusSpan.classList.add("erro");
      }
      return;
    }

    const { status, data } = await apiPost("/api/sensores", {
      id,
      tipo,
      modelo: modelo || null,
      localizacao: localizacao || null,
    });

    if (status === 201) {
      if (statusSpan) {
        statusSpan.textContent = data.message || "Sensor cadastrado.";
        statusSpan.classList.remove("erro");
        statusSpan.classList.add("ok");
      }
      form.reset();
      await carregarSensores();
    } else {
      if (statusSpan) {
        statusSpan.textContent = data.error || "Erro ao cadastrar sensor.";
        statusSpan.classList.remove("ok");
        statusSpan.classList.add("erro");
      }
    }
  });

  if (btnLimpar) {
    btnLimpar.addEventListener("click", async () => {
      const confirma = confirm(
        "Tem certeza que deseja limpar os sensores do XML?"
      );
      if (!confirma) return;

      const { status, data } = await apiDelete("/api/sensores");
      if (status === 200) {
        if (statusSpan) {
          statusSpan.textContent = data.message || "Sensores limpos.";
          statusSpan.classList.remove("erro");
          statusSpan.classList.add("ok");
        }
        await carregarSensores();
      } else {
        if (statusSpan) {
          statusSpan.textContent = data.error || "Erro ao limpar sensores.";
          statusSpan.classList.remove("ok");
          statusSpan.classList.add("erro");
        }
      }
    });
  }

  carregarSensores();
}

// ======================= ATUADORES =======================

async function carregarAtuadores() {
  const tabela = document.getElementById("tabela-atuadores");
  if (!tabela) return;

  const tbody = tabela.querySelector("tbody");
  const { status, data } = await apiGet("/api/atuadores");
  if (status !== 200) return;

  tbody.innerHTML = "";

  const atuadores = data.slice();

  atuadores.forEach((a) => {
    const ultimo = a.ultimoComando
      ? `${formatDataHora(a.ultimoComando.dataHora)} (${a.ultimoComando.acao})`
      : "-";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${a.id}</td>
      <td>${a.tipo}</td>
      <td>${ultimo}</td>
      <td>${(a.comandos || []).length}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function carregarComandos() {
  const tabela = document.getElementById("tabela-comandos");
  if (!tabela) return;

  const tbody = tabela.querySelector("tbody");
  const { status, data } = await apiGet("/api/atuadores/comandos");
  if (status !== 200) return;

  tbody.innerHTML = "";

  data.forEach((c) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${c.atuadorId}</td>
      <td>${c.tipo || "-"}</td>
      <td>${c.acao || "-"}</td>
      <td>${formatDataHora(c.dataHora)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function initAtuadoresPage() {
  const form = document.getElementById("form-atuador");
  const tabelaAtuadores = document.getElementById("tabela-atuadores");
  if (!form || !tabelaAtuadores) return; // não está na página de atuadores

  const statusSpan = document.getElementById("status-atuador");
  const btnLimparAtuadores = document.getElementById("btn-limpar-atuadores");
  const btnLimparHistorico = document.getElementById(
    "btn-limpar-historico-comandos"
  );

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const id = document.getElementById("atuadorId").value.trim();
    const tipo = document.getElementById("atuadorTipo").value.trim();

    if (!id || !tipo) {
      if (statusSpan) {
        statusSpan.textContent = "Preencha ID e tipo.";
        statusSpan.classList.add("erro");
      }
      return;
    }

    const { status, data } = await apiPost("/api/atuadores", {
      id,
      tipo,
    });

    if (status === 201) {
      if (statusSpan) {
        statusSpan.textContent = data.message || "Atuador cadastrado.";
        statusSpan.classList.remove("erro");
        statusSpan.classList.add("ok");
      }
      form.reset();
      await carregarAtuadores();
    } else {
      if (statusSpan) {
        statusSpan.textContent = data.error || "Erro ao cadastrar atuador.";
        statusSpan.classList.remove("ok");
        statusSpan.classList.add("erro");
      }
    }
  });

  // limpar todos os atuadores (XML)
  if (btnLimparAtuadores) {
    btnLimparAtuadores.addEventListener("click", async () => {
      const confirma = confirm(
        "Tem certeza que deseja remover TODOS os atuadores do XML?"
      );
      if (!confirma) return;

      const { status, data } = await apiDelete("/api/atuadores");
      if (status === 200) {
        if (statusSpan) {
          statusSpan.textContent = data.message || "Atuadores limpos.";
          statusSpan.classList.remove("erro");
          statusSpan.classList.add("ok");
        }
        await carregarAtuadores();
        await carregarComandos(); // histórico some também
      } else {
        if (statusSpan) {
          statusSpan.textContent = data.error || "Erro ao limpar atuadores.";
          statusSpan.classList.remove("ok");
          statusSpan.classList.add("erro");
        }
      }
    });
  }

  // limpar apenas o histórico de comandos
  if (btnLimparHistorico) {
    btnLimparHistorico.addEventListener("click", async () => {
      const confirma = confirm(
        "Tem certeza que deseja limpar apenas o histórico de operações dos atuadores?"
      );
      if (!confirma) return;

      const { status, data } = await apiDelete("/api/atuadores/comandos");
      if (status === 200) {
        if (statusSpan) {
          statusSpan.textContent =
            data.message || "Histórico de operações limpo.";
          statusSpan.classList.remove("erro");
          statusSpan.classList.add("ok");
        }
        await carregarAtuadores();
        await carregarComandos();
      } else {
        if (statusSpan) {
          statusSpan.textContent =
            data.error || "Erro ao limpar histórico de operações.";
          statusSpan.classList.remove("ok");
          statusSpan.classList.add("erro");
        }
      }
    });
  }

  // primeira carga
  carregarAtuadores();
  carregarComandos();
}

// ========= LEITURAS / ALERTAS (PÁGINA ALERTAS) ==========

async function carregarLeituras() {
  const tabela = document.getElementById("tabela-leituras");
  if (!tabela) return;

  const tbody = tabela.querySelector("tbody");
  const { status, data } = await apiGet("/api/leituras");
  if (status !== 200) return;

  tbody.innerHTML = "";

  data.forEach((l) => {
    const tr = document.createElement("tr");

    // se estiver fora da faixa, aplica a classe CSS
    if (l.foraFaixa) {
      tr.classList.add("fora-faixa");
    }

    tr.innerHTML = `
      <td>${l.sensorId}</td>
      <td>${l.tipo || "-"}</td>
      <td>${formatValor(l.valor)}</td>
      <td>${formatUnidade(l.unidade)}</td>
      <td>${l.mensagem}</td>
      <td>${formatDataHora(l.dataHora)}</td>
    `;

    tbody.appendChild(tr);
  });
}

function toIsoWithZFromLocal(localValue) {
  if (!localValue) return null;
  // datetime-local vem sem segundos, adiciono ":00Z"
  return localValue + ":00Z";
}

function initAlertasPage() {
  const tabelaLeituras = document.getElementById("tabela-leituras");
  if (!tabelaLeituras) return; // não está na página de alertas

  const btnLimparLeituras = document.getElementById("btn-limpar-leituras");
  const btnExportXml = document.getElementById("btn-exportar-xml");
  const inputInicio = document.getElementById("exportInicio");
  const inputFim = document.getElementById("exportFim");
  const statusSpan = document.getElementById("status-alertas");

  // botão de limpar leituras (DELETE /api/leituras)
  if (btnLimparLeituras) {
    btnLimparLeituras.addEventListener("click", async () => {
      const confirma = confirm(
        "Tem certeza que deseja limpar o histórico de leituras no XML?"
      );
      if (!confirma) return;

      const { status, data } = await apiDelete("/api/leituras");
      if (status === 200) {
        if (statusSpan) {
          statusSpan.textContent = data.message || "Leituras limpas.";
          statusSpan.classList.remove("erro");
          statusSpan.classList.add("ok");
        }
        await carregarLeituras();
      } else {
        if (statusSpan) {
          statusSpan.textContent = data.error || "Erro ao limpar leituras.";
          statusSpan.classList.remove("ok");
          statusSpan.classList.add("erro");
        }
      }
    });
  }

  // botão de exportar XML filtrado por data (GET /api/exportar/xml)
  if (btnExportXml) {
    btnExportXml.addEventListener("click", () => {
      const inicioLocal = inputInicio.value;
      const fimLocal = inputFim.value;

      if (!inicioLocal || !fimLocal) {
        alert("Preencha as datas de início e fim.");
        return;
      }

      const inicioIso = toIsoWithZFromLocal(inicioLocal);
      const fimIso = toIsoWithZFromLocal(fimLocal);

      const url = `/api/exportar/xml?inicio=${encodeURIComponent(
        inicioIso
      )}&fim=${encodeURIComponent(fimIso)}`;

      window.open(url, "_blank");
    });
  }

  // loop de simulação "tempo real"
  async function tickSimulacao() {
    // chama o "gateway" com X-API-KEY
    await apiPost("/api/simulacao/tick", {}, { asDevice: true });
    await apiPost("/api/sync-pendentes", {}, { asDevice: true });

    await carregarLeituras();
  }

  // primeira carga
  carregarLeituras();
  tickSimulacao();

  // intervalo periódico
  setInterval(tickSimulacao, 5000);
}

// ======================= BOOTSTRAP =======================

document.addEventListener("DOMContentLoaded", () => {
  initSensoresPage();
  initAtuadoresPage();
  initAlertasPage();
});
