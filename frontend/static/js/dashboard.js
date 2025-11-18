const API_KEY = "chave-dev-exemplo";

const unidadeFriendly = {
  "°C": "°C (Graus Celsius)",
  "mS/cm": "mS/cm (Condutividade elétrica)",
  "%": "% (Percentual)",
  "lux": "lux (Luminosidade)",
  "pH": "pH",
};

function formatUnidade(u) {
  if (!u) return "";
  return unidadeFriendly[u] || u;
}

function formatStatus(status) {
  switch (status) {
    case "ok":
      return "Dentro da faixa ideal";
    case "critico-baixo":
      return "Abaixo da faixa ideal";
    case "critico-alto":
      return "Acima da faixa ideal";
    default:
      return "Desconhecido";
  }
}

/* ---------- API AUX ---------- */

async function apiGet(url) {
  const resp = await fetch(url);
  return resp.json();
}

async function apiPost(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return resp.json().then((data) => ({ status: resp.status, data }));
}

async function apiDelete(url) {
  const resp = await fetch(url, { method: "DELETE" });
  return resp.json();
}

/* ---------- PÁGINA: SENSORES ---------- */

async function carregarSensores() {
  const tbody = document.querySelector("#tabela-sensores tbody");
  if (!tbody) return;

  let dados = await apiGet("/api/sensores");
  tbody.innerHTML = "";

  // último cadastrado vem primeiro
  dados.slice().reverse().forEach((s) => {
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
  const marker = document.getElementById("page-sensores");
  if (!marker) return;

  const form = document.getElementById("form-sensor");
  const statusSpan = document.getElementById("status-sensor");
  const btnLimpar = document.getElementById("btn-limpar-sensores");

  if (form) {
        form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = document.getElementById("sensorId").value.trim();
      const tipo = document.getElementById("sensorTipo").value;
      const modelo = document.getElementById("sensorModelo").value.trim();
      const localizacao = document.getElementById("sensorLocal").value.trim();

      if (!id || !tipo) {
        statusSpan.textContent = "Preencha os campos obrigatórios.";
        statusSpan.classList.add("erro");
        return;
      }

      const { status, data } = await apiPost("/api/sensores", {
        id,
        tipo,
        modelo: modelo || null,
        localizacao: localizacao || null,
      });

      if (status === 201) {
        statusSpan.textContent = data.message;
        statusSpan.classList.remove("erro");
        statusSpan.classList.add("ok");
        form.reset();
        await carregarSensores();
      } else {
        statusSpan.textContent = data.error || "Erro ao cadastrar sensor.";
        statusSpan.classList.remove("ok");
        statusSpan.classList.add("erro");
      }
    });
  }

  if (btnLimpar) {
  btnLimpar.addEventListener("click", async () => {
    const res = await apiDelete("/api/sensores");
    if (res.error) {
      alert("Erro ao limpar sensores: " + res.error);
    } else {
      alert(res.message || "Sensores limpos.");
    }
    await carregarSensores();
  });
}

  carregarSensores();
}

/* ---------- PÁGINA: ATUADORES ---------- */

async function carregarAtuadores() {
  const tbody = document.querySelector("#tabela-atuadores tbody");
  if (!tbody) return;

  let dados = await apiGet("/api/atuadores");
  tbody.innerHTML = "";

  // atuadores: mais novo primeiro
  dados.slice().reverse().forEach((a) => {
    // comandos também: mais recente em cima
    const comandosOrdenados = (a.comandos || []).slice().sort(
      (c1, c2) => new Date(c2.dataHora) - new Date(c1.dataHora)
    );

    let comandosHTML = "";
    if (!comandosOrdenados.length) {
      comandosHTML = "<em>Nenhum comando registrado</em>";
    } else {
      comandosHTML = "<ul>";
      comandosOrdenados.forEach((c) => {
        comandosHTML += `<li>${new Date(c.dataHora).toLocaleString()} — ${c.acao}</li>`;
      });
      comandosHTML += "</ul>";
    }

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${a.id}</td>
      <td>${a.tipo}</td>
      <td>${comandosHTML}</td>
    `;
    tbody.appendChild(tr);
  });
}

function initAtuadoresPage() {
  const marker = document.getElementById("page-atuadores");
  if (!marker) return;

  const form = document.getElementById("form-atuador");
  const statusSpan = document.getElementById("status-atuador");
  const btnLimpar = document.getElementById("btn-limpar-atuadores");

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = document.getElementById("atuadorId").value.trim();
      const tipo = document.getElementById("atuadorTipo").value;

      if (!id || !tipo) {
        statusSpan.textContent = "Preencha os campos obrigatórios.";
        statusSpan.classList.add("erro");
        return;
      }

      const { status, data } = await apiPost("/api/atuadores", {
        id,
        tipo,
      });

      if (status === 201) {
        statusSpan.textContent = data.message;
        statusSpan.classList.remove("erro");
        statusSpan.classList.add("ok");
        form.reset();
        await carregarAtuadores();
      } else {
        statusSpan.textContent = data.error || "Erro ao cadastrar atuador.";
        statusSpan.classList.remove("ok");
        statusSpan.classList.add("erro");
      }
    });
  }

  if (btnLimpar) {
  btnLimpar.addEventListener("click", async () => {
    const res = await apiDelete("/api/atuadores");
    if (res.error) {
      alert("Erro ao limpar atuadores: " + res.error);
    } else {
      alert(res.message || "Atuadores limpos.");
    }
    await carregarAtuadores();
  });
}

  carregarAtuadores();
}

/* ---------- PÁGINA: ALERTAS ---------- */

async function carregarAlertasTabela() {
  const tbody = document.querySelector("#tabela-alertas tbody");
  if (!tbody) return;

  let dados = await apiGet("/api/alertas");
  tbody.innerHTML = "";

  if (dados.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="5"><em>Sem alertas no momento.</em></td>`;
    tbody.appendChild(tr);
    return;
  }

  // mais recente primeiro
  dados.sort((a, b) => new Date(b.dataHora) - new Date(a.dataHora));

  dados.forEach((a) => {
    const tr = document.createElement("tr");
    tr.classList.add("linha-critica");
    tr.innerHTML = `
      <td>${new Date(a.dataHora).toLocaleString()}</td>
      <td>${a.sensorId}</td>
      <td>${a.tipo}</td>
      <td>${a.valor}</td>
      <td>${a.mensagem}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function carregarLeiturasTabelaSimples() {
  const tbody = document.querySelector("#tabela-leituras tbody");
  if (!tbody) return;

  let dados = await apiGet("/api/leituras");
  tbody.innerHTML = "";

  // mais recente primeiro
  dados.sort((a, b) => new Date(b.dataHora) - new Date(a.dataHora));

  dados.forEach((l) => {
    const tr = document.createElement("tr");
    if (l.status === "ok") tr.classList.add("linha-ok");
    if (l.status && l.status.startsWith("critico")) tr.classList.add("linha-critica");

    tr.innerHTML = `
      <td>${new Date(l.dataHora).toLocaleString()}</td>
      <td>${l.sensorId}</td>
      <td>${l.tipo || ""}</td>
      <td>${l.valor}</td>
      <td>${formatUnidade(l.unidade)}</td>
      <td>${formatStatus(l.status)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function toIsoWithZFromLocal(localValue) {
  // localValue vem do input datetime-local (ex: "2025-10-24T10:00")
  if (!localValue) return null;
  // assume timezone local como UTC para fins acadêmicos
  return localValue + ":00Z";
}

function initAlertasPage() {
  const marker = document.getElementById("page-alertas");
  if (!marker) return;

  const btnSimular = document.getElementById("btn-simular-ciclo");
  const btnLimpar = document.getElementById("btn-limpar-leituras");

  if (btnSimular) {
    btnSimular.addEventListener("click", async () => {
      await apiPost("/api/simulacao/tick", {});
      await carregarLeiturasTabelaSimples();
      await carregarAlertasTabela();
    });
  }

  if (btnLimpar) {
  btnLimpar.addEventListener("click", async () => {
    const res = await apiDelete("/api/leituras");
    if (res.error) {
      alert("Erro ao limpar histórico: " + res.error);
    } else {
      alert(res.message || "Histórico limpo.");
    }
    await carregarLeiturasTabelaSimples();
    await carregarAlertasTabela();
  });

  const btnExport = document.getElementById("btn-exportar-xml");
  const inputInicio = document.getElementById("exportInicio");
  const inputFim = document.getElementById("exportFim");

  if (btnExport) {
    btnExport.addEventListener("click", () => {
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

      // abre o download do XML em nova aba
      window.open(url, "_blank");
    });
  }
}

  // carga inicial
  carregarLeiturasTabelaSimples();
  carregarAlertasTabela();

  // atualização automática leve
  setInterval(async () => {
    await apiPost("/api/simulacao/tick", {});
    await carregarLeiturasTabelaSimples();
    await carregarAlertasTabela();
  }, 5000);
}

/* ---------- INIT GERAL ---------- */

window.addEventListener("load", () => {
  initSensoresPage();
  initAtuadoresPage();
  initAlertasPage();
});
