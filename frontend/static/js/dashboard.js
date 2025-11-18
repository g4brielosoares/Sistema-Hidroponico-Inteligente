const unidadeFriendly = {
  "°C": "°C (Graus Celsius)",
  "mS/cm": "mS/cm (Condutividade elétrica)",
  "%": "% (Percentual)",
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

async function carregarLeituras() {
  try {
    const resp = await fetch("/api/leituras");
    const dados = await resp.json();

    const tbody = document.querySelector("#tabela-leituras tbody");
    tbody.innerHTML = "";

    dados.forEach(l => {
      const tr = document.createElement("tr");

      if (l.status && l.status.startsWith("critico")) {
        tr.classList.add("linha-critica");
      } else if (l.status === "ok") {
        tr.classList.add("linha-ok");
      }

      tr.innerHTML = `
        <td>${new Date(l.dataHora).toLocaleString()}</td>
        <td>${l.sensorId}</td>
        <td>${l.tipo || ""}</td>
        <td>${l.valor}</td>
        <td>${formatUnidade(l.unidade)}</td>
        <td>${formatStatus(l.status)}</td>
        <td>${l.alerta || ""}</td>
      `;
      tbody.appendChild(tr);
    });

    carregarAlertas();
  } catch (e) {
    console.error("Erro ao carregar leituras", e);
  }
}

async function carregarAlertas() {
  try {
    const resp = await fetch("/api/alertas");
    const dados = await resp.json();

    const alertasDiv = document.getElementById("alertas");
    alertasDiv.innerHTML = "<h3>Alertas Atuais</h3>";

    if (dados.length === 0) {
      alertasDiv.innerHTML += "<p>Sem alertas no momento.</p>";
      return;
    }

    const ul = document.createElement("ul");
    dados.forEach(a => {
      const li = document.createElement("li");
      li.textContent = `${a.tipo} (${a.sensorId}) em ${new Date(a.dataHora).toLocaleString()}: ${a.mensagem}`;
      ul.appendChild(li);
    });

    alertasDiv.appendChild(ul);
  } catch (e) {
    console.error("Erro ao carregar alertas", e);
  }
}

setInterval(carregarLeituras, 5000);
window.addEventListener("load", carregarLeituras);
