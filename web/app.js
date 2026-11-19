// Demo web de HVAC Tools.
// Carga Pyodide (Python compilado a WebAssembly), copia los módulos del
// repositorio a su sistema de archivos y llama a web/api.py. Toda la lógica
// de cálculo vive en Python; este archivo solo arma la interfaz.

"use strict";

const MODULOS = [
  "carga_termica/carga_termica.py",
  "conversor_unidades/conversor_unidades.py",
  "psicrometria/psicrometria.py",
  "ductos/ductos.py",
  "consumo_energetico/consumo_energetico.py",
  "web/api.py",
];

// useGrouping "always": en español "1.365" en lugar de "1365", igual que "11.000".
const fmt = (n, dec = 0) =>
  Number(n).toLocaleString("es", { minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: "always" });
const fmtAuto = (n) => {
  const a = Math.abs(n);
  if (a !== 0 && (a >= 1e7 || a < 1e-3)) return Number(n).toExponential(4);
  return Number(n).toLocaleString("es", { maximumFractionDigits: a < 10 ? 4 : 2, useGrouping: "always" });
};
const escapar = (t) =>
  String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

let ejecutarPy = null;

function llamar(nombre, params = {}) {
  const r = JSON.parse(ejecutarPy(nombre, JSON.stringify(params)));
  if (!r.ok) throw new Error(r.error);
  return r.datos;
}

function datosFormulario(form) {
  const datos = {};
  for (const el of form.elements) {
    if (!el.name || el.value === "") continue;
    if ((el.type === "radio" || el.type === "checkbox") && !el.checked) continue;
    // Campos de otro modo / forma (ocultos dentro del formulario). La pestaña
    // entera puede estar oculta y sus campos deben enviarse igual.
    const oculto = el.closest("[hidden]");
    if (oculto && form.contains(oculto)) continue;
    datos[el.name] = el.value;
  }
  return datos;
}

const kpi = (titulo, valor, unidad = "", destacado = false) => `
  <div class="kpi${destacado ? " destacado" : ""}">
    <div class="titulo">${titulo}</div>
    <div class="valor">${valor}<span class="unidad">${unidad}</span></div>
  </div>`;

// ---------- Renderizadores por herramienta ----------

const NOMBRES_CARGA = {
  envolvente: "Envolvente", ventanas: "Ventanas", personas: "Personas",
  equipos: "Equipos", seguridad: "Seguridad",
};

const render = {
  carga(form) {
    const d = llamar("carga", datosFormulario(form));
    const max = Math.max(...Object.values(d.desglose));
    const barras = Object.entries(d.desglose).map(([k, v]) => `
      <div class="barra">
        <span>${NOMBRES_CARGA[k] ?? k}</span>
        <div class="pista"><div class="relleno" style="width:${max ? (v / max) * 100 : 0}%"></div></div>
        <span class="cifra">${fmt(v)} BTU/h</span>
      </div>`).join("");
    const equipo = d.equipo_btu_h
      ? kpi("Equipo sugerido", fmt(d.equipo_btu_h), " BTU/h", true)
      : kpi("Equipo sugerido", "Sistema central", "", true);
    return `
      <h2>Resultado</h2>
      <div class="kpis">
        ${equipo}
        ${kpi("Carga total", fmt(d.total_btu_h), " BTU/h")}
        ${kpi("Potencia", fmt(d.total_kw, 2), " kW")}
        ${kpi("Toneladas", fmt(d.total_tr, 2), " TR")}
      </div>
      <h2>Desglose</h2>
      <div class="barras">${barras}</div>`;
  },

  conversor(form) {
    const p = datosFormulario(form);
    const d = llamar("conversor", p);
    const filas = Object.entries(d.tabla).map(([u, v]) => `
      <tr class="${u === d.destino ? "activa" : ""}"><td>${escapar(u)}</td><td class="num">${fmtAuto(v)}</td></tr>`).join("");
    return `
      <h2>Resultado</h2>
      <div class="kpis">
        ${kpi(`${fmtAuto(p.valor)} ${escapar(d.origen)} =`, fmtAuto(d.resultado), " " + escapar(d.destino), true)}
      </div>
      <h2>Todas las equivalencias</h2>
      <table class="tabla"><thead><tr><th>Unidad</th><th class="num">Valor</th></tr></thead><tbody>${filas}</tbody></table>`;
  },

  psicrometria(form) {
    const d = llamar("psicrometria", datosFormulario(form));
    const filas = [
      ["Bulbo seco", fmt(d.tbs_c, 2), "°C"],
      ["Humedad relativa", fmt(d.hr_pct, 1), "%"],
      ["Bulbo húmedo", fmt(d.tbh_c, 2), "°C"],
      ["Punto de rocío", fmt(d.rocio_c, 2), "°C"],
      ["Humedad absoluta", fmt(d.w_g_kg, 2), "g/kg aire seco"],
      ["Entalpía", fmt(d.entalpia_kj_kg, 2), "kJ/kg aire seco"],
      ["Volumen específico", fmt(d.volumen_m3_kg, 4), "m³/kg aire seco"],
      ["Densidad", fmt(d.densidad_kg_m3, 4), "kg/m³"],
      ["Presión atmosférica", fmt(d.presion_kpa, 3), "kPa"],
    ].map(([n, v, u]) => `<tr><td>${n}</td><td class="num">${v}</td><td>${u}</td></tr>`).join("");
    return `
      <h2>Resultado</h2>
      <div class="kpis">
        ${kpi("Punto de rocío", fmt(d.rocio_c, 1), " °C", true)}
        ${kpi("Bulbo húmedo", fmt(d.tbh_c, 1), " °C")}
        ${kpi("Entalpía", fmt(d.entalpia_kj_kg, 1), " kJ/kg")}
      </div>
      <table class="tabla"><tbody>${filas}</tbody></table>`;
  },

  ductos(form) {
    const d = llamar("ductos", datosFormulario(form));
    const u = d.unidad_medida;
    const dec = u === "mm" ? 0 : 1;
    // Redondea antes de decidir decimales: 0,35 m / 0,01 da 34,999… en coma flotante.
    const med = (x) => {
      const r = Math.round(x * 10) / 10;
      return fmt(r, Number.isInteger(r) ? 0 : dec);
    };
    const [vMin, vMax] = d.rango_velocidad;
    const lista = d.avisos.length
      ? `<ul class="avisos">${d.avisos.map((a) => `<li>${escapar(a)}</li>`).join("")}</ul>`
      : "";
    const caudal = `<tr><td>Caudal</td><td class="num">${fmt(d.caudal_m3h)} m³/h · ${fmt(d.caudal_cfm)} CFM</td></tr>`;

    if (d.modo === "verificar") {
      const velAlta = Math.round(d.velocidad_ms * 1000) / 1000 > vMax;
      const velBaja = Math.round(d.velocidad_ms * 1000) / 1000 < vMin;
      const estadoVel = velAlta ? " peligro" : velBaja ? "" : " correcto";
      const medida = d.forma === "rectangular"
        ? `${med(d.ancho)} × ${med(d.alto)} ${u}`
        : `Ø ${med(d.diametro)} ${u}`;
      let sugerencia = "";
      if (d.sugerido) {
        const s = d.sugerido;
        const texto = s.forma === "rectangular" ? `${med(s.ancho)} × ${med(s.alto)}` : `Ø ${med(s.diametro)}`;
        sugerencia = kpi("Tamaño mínimo recomendado", texto, ` ${u} · ${fmt(s.velocidad_ms, 1)} m/s`, true);
      }
      const veredicto = velAlta || velBaja
        ? ""
        : `<p class="mensaje-ok">Ducto adecuado: velocidad dentro del rango recomendado.</p>`;
      return `
        <h2>Verificación del ducto ${escapar(medida)}</h2>
        <div class="kpis">
          <div class="kpi${estadoVel}">
            <div class="titulo">Velocidad del aire</div>
            <div class="valor">${fmt(d.velocidad_ms, 1)}<span class="unidad"> m/s</span></div>
            <div class="titulo">Recomendado ${fmt(vMin, 1)}–${fmt(vMax, 1)} m/s</div>
          </div>
          ${kpi("Fricción", fmt(d.friccion_pa_m, 2), " Pa/m")}
          ${sugerencia}
        </div>
        <table class="tabla"><tbody>
          ${caudal}
          <tr><td>Área libre</td><td class="num">${fmt(d.area_m2, 4)} m²</td></tr>
          ${d.forma === "rectangular" ? `<tr><td>Diámetro equivalente</td><td class="num">${med(d.diametro)} ${u}</td></tr>` : ""}
        </tbody></table>
        ${lista}${veredicto}`;
    }

    const [ancho, alto] = d.rectangular_comercial;
    return `
      <h2>Resultado</h2>
      <div class="kpis">
        ${kpi("Ducto circular", "Ø " + med(d.diametro_comercial), " " + u, true)}
        ${kpi("Ducto rectangular", `${med(ancho)} × ${med(alto)}`, " " + u, true)}
        ${kpi("Velocidad", fmt(d.velocidad_ms, 2), " m/s")}
        ${kpi("Fricción", fmt(d.friccion_pa_m, 3), " Pa/m")}
      </div>
      <table class="tabla"><tbody>
        ${caudal}
        <tr><td>Diámetro calculado</td><td class="num">${fmt(d.diametro, dec)} ${u}</td></tr>
        <tr><td>Rectangular calculado</td><td class="num">${fmt(d.ancho, dec)} × ${fmt(d.alto, dec)} ${u}</td></tr>
      </tbody></table>
      ${lista || `<p class="mensaje-ok">Velocidad dentro del rango recomendado.</p>`}`;
  },

  comparar(form) {
    const d = llamar("comparar", datosFormulario(form));
    const tarjeta = (nombre, c) => `
      <div class="kpi">
        <div class="titulo">${nombre}</div>
        <div class="valor">$${fmt(c.costo_mes, 2)}<span class="unidad">/mes</span></div>
        <div class="titulo">${fmt(c.potencia_kw, 2)} kW · ${fmt(c.kwh_mes)} kWh/mes · $${fmt(c.costo_anual, 2)}/año</div>
      </div>`;
    let retorno;
    if (d.retorno_anios === null) retorno = "No se recupera";
    else if (d.retorno_anios === 0) retorno = "Inmediato";
    else retorno = `${fmt(d.retorno_anios, 1)} años`;
    const ahorroTxt = d.ahorro_anual >= 0 ? "Ahorro anual con B" : "Gasto extra anual con B";
    return `
      <h2>Costo de operación</h2>
      <div class="comparacion">${tarjeta("Equipo A", d.equipo_a)}${tarjeta("Equipo B", d.equipo_b)}</div>
      <div class="kpis">
        ${kpi(ahorroTxt, "$" + fmt(Math.abs(d.ahorro_anual), 2), "", true)}
        ${kpi("Sobrecosto de B", "$" + fmt(d.diferencia_precio, 2))}
        ${kpi("Retorno de la inversión", retorno, "", true)}
      </div>`;
  },
};

const PANEL_A_RESULTADO = {
  carga: "res-carga", conversor: "res-conversor", psicrometria: "res-psicrometria",
  ductos: "res-ductos", comparar: "res-consumo",
};

function actualizar(form) {
  const herramienta = form.dataset.herramienta;
  const destino = document.getElementById(PANEL_A_RESULTADO[herramienta]);
  if (!ejecutarPy) return;
  try {
    destino.innerHTML = render[herramienta](form);
  } catch (e) {
    destino.innerHTML = `<h2>Resultado</h2><p class="error">${escapar(e.message)}</p>`;
  }
}

// ---------- Conversor: listas de unidades ----------

let UNIDADES = {};
const NOMBRES_MAGNITUD = {
  potencia: "Potencia térmica", caudal: "Caudal de aire", presion: "Presión",
  energia: "Energía", temperatura: "Temperatura",
};
const POR_DEFECTO = {
  potencia: ["BTU/h", "TR"], caudal: ["CFM", "m3/h"], presion: ["inH2O", "Pa"],
  energia: ["kWh", "BTU"], temperatura: ["C", "F"],
};

function llenarUnidades(magnitud) {
  const opciones = UNIDADES[magnitud].map((u) => `<option>${escapar(u)}</option>`).join("");
  const origen = document.getElementById("conv-origen");
  const destino = document.getElementById("conv-destino");
  origen.innerHTML = destino.innerHTML = opciones;
  [origen.value, destino.value] = POR_DEFECTO[magnitud];
}

function prepararConversor() {
  UNIDADES = llamar("unidades");
  const sel = document.getElementById("conv-magnitud");
  sel.innerHTML = Object.keys(UNIDADES)
    .map((m) => `<option value="${m}">${NOMBRES_MAGNITUD[m] ?? m}</option>`).join("");
  sel.addEventListener("change", () => {
    llenarUnidades(sel.value);
    const form = sel.form;
    form.elements.valor.value = sel.value === "temperatura" ? 24 : 1;
    actualizar(form);
  });
  llenarUnidades("potencia");
}

// ---------- Pestañas y eventos ----------

function prepararPestanas() {
  const botones = document.querySelectorAll(".pestanas button");
  botones.forEach((b) => b.addEventListener("click", () => {
    botones.forEach((o) => o.setAttribute("aria-selected", String(o === b)));
    document.querySelectorAll(".panel").forEach((p) => { p.hidden = p.id !== `panel-${b.dataset.panel}`; });
    history.replaceState(null, "", `#${b.dataset.panel}`);
  }));
  const abrirDesdeHash = () => {
    const boton = [...botones].find((b) => b.dataset.panel === location.hash.slice(1));
    if (boton) boton.click();
  };
  window.addEventListener("hashchange", abrirDesdeHash);
  abrirDesdeHash();
}

// Ductos: muestra los campos del modo / forma elegidos y convierte cm <-> mm.
function prepararDuctos() {
  const form = document.querySelector('[data-herramienta="ductos"]');
  const medidas = ["alto_fijo", "ancho", "alto", "diametro"];
  let unidadAnterior = form.elements.unidad_medida.value;
  const sincronizar = () => {
    const modo = form.querySelector('input[name="modo"]:checked').value;
    const forma = form.elements.forma.value;
    form.querySelectorAll("[data-solo-modo]").forEach((el) => { el.hidden = el.dataset.soloModo !== modo; });
    form.querySelectorAll("[data-solo-forma]").forEach((el) => { el.hidden = el.dataset.soloForma !== forma; });
    const unidad = form.elements.unidad_medida.value;
    if (unidad !== unidadAnterior) {
      const factor = unidad === "mm" ? 10 : 0.1;
      medidas.forEach((n) => {
        const el = form.elements[n];
        if (el.value !== "") el.value = +(Number(el.value) * factor).toFixed(1);
      });
      unidadAnterior = unidad;
    }
    form.querySelectorAll(".u-medida").forEach((s) => { s.textContent = unidad; });
  };
  form.addEventListener("change", sincronizar);
  sincronizar();
}

function prepararFormularios() {
  prepararDuctos();
  document.querySelectorAll("form.formulario").forEach((form) => {
    let espera;
    const programar = () => { clearTimeout(espera); espera = setTimeout(() => actualizar(form), 150); };
    form.addEventListener("input", programar);
    form.addEventListener("change", programar);
    form.addEventListener("submit", (e) => e.preventDefault());
  });
}

async function iniciar() {
  prepararPestanas();
  prepararFormularios();
  const aviso = document.getElementById("estado-carga");
  const texto = document.getElementById("estado-texto");
  try {
    const pyodide = await loadPyodide();
    texto.textContent = "Cargando los módulos de cálculo…";
    const archivos = await Promise.all(MODULOS.map(async (ruta) => {
      const resp = await fetch(ruta);
      if (!resp.ok) throw new Error(`No se pudo cargar ${ruta}`);
      return [ruta, await resp.text()];
    }));
    const base = "/home/pyodide/hvac";
    pyodide.FS.mkdirTree(base);
    for (const [ruta, codigo] of archivos) {
      const carpeta = `${base}/${ruta.split("/")[0]}`;
      pyodide.FS.mkdirTree(carpeta);
      pyodide.FS.writeFile(`${carpeta}/__init__.py`, "");
      pyodide.FS.writeFile(`${base}/${ruta}`, codigo);
    }
    pyodide.runPython(`import sys; sys.path.insert(0, "${base}")`);
    ejecutarPy = pyodide.pyimport("web.api").ejecutar;
    prepararConversor();
    document.querySelectorAll("form.formulario").forEach(actualizar);
    aviso.classList.add("oculto");
  } catch (e) {
    aviso.classList.add("error");
    aviso.querySelector(".spinner")?.remove();
    texto.textContent = `No se pudo iniciar Python en el navegador: ${e.message}`;
    console.error(e);
  }
}

iniciar();
