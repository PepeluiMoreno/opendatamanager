<template>
  <div class="help">
    <header class="help-head">
      <h1>Help</h1>
      <p class="sub">Protocolo productor / consumidor</p>
    </header>

    <div class="help-body">
      <p><b>OpenDataManager</b> es el <b>productor</b>: cosecha y versiona datos y los expone por GraphQL y webhooks. Las aplicaciones <b>consumidoras</b> (p. ej. ckan-jerez) se dan de alta, se suscriben a recursos o colecciones, y pueden proponer nuevos.</p>

      <h2>Gobernanza (Subscribers → Pendientes)</h2>
      <ol>
        <li><b>Solicitudes de alta</b>: una aplicación pide ingresar. Al <b>aprobarla</b> se materializa su principal y se emite un <b>token</b> (visible una sola vez).</li>
        <li><b>Recursos propuestos</b>: lo creado por una aplicación nace <i>pendiente</i> y no se ejecuta hasta que un administrador lo <b>aprueba</b> (o lo rechaza con motivo).</li>
        <li><b>Tokens</b>: por aplicación se pueden emitir, rotar o revocar.</li>
      </ol>

      <h2>Recursos «nodriza» (recursos con hijos)</h2>
      <p>Un crawler raíz afecta al sitio de origen, por eso <b>se proponen desde las aplicaciones pero se aprueban e instancian aquí</b>, en ODM. El productor gobierna coste e impacto externo; el consumidor propone y consume.</p>

      <h2>Colecciones y suscripciones</h2>
      <p>Las <b>colecciones</b> son conjuntos (no disjuntos) del pool de recursos: un recurso puede estar en varias. Un <b>suscriptor</b> puede suscribirse a una colección (recibe todos sus recursos, incluidos los que se añadan después) o a recursos sueltos. Suscribirse a una nodriza cubre toda su familia.</p>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.help{max-width:820px;margin:0 auto;padding:28px 24px;color:#E7EEF6}
.help-head h1{margin:0;font-size:24px;font-weight:700}
.help-head .sub{margin:4px 0 0;color:#8595A6;font-size:14px}
.help-body{margin-top:20px;font-size:14px;line-height:1.65;color:#C7D2DD}
.help-body h2{margin:24px 0 8px;font-size:15px;font-weight:600;color:#3FE0CB}
.help-body ol{margin:8px 0;padding-left:20px}
.help-body li{margin:4px 0}
.help-body b{color:#E7EEF6}
</style>
