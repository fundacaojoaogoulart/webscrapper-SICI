// Inicialização local do Mermaid (sem CDN).
// Este arquivo é carregado depois de mermaid.min.js via extra_javascript.
(function () {
  function render() {
    if (typeof mermaid === "undefined") return;
    try {
      mermaid.run({ querySelector: ".mermaid" });
    } catch (e) {
      // Diagrama já renderizado em uma navegação anterior.
    }
  }

  function boot() {
    if (typeof mermaid === "undefined") return;
    mermaid.initialize({
      startOnLoad: false,
      theme: "neutral",
      securityLevel: "loose",
      flowchart: { htmlLabels: true, curve: "basis" },
      themeVariables: { fontFamily: "inherit" }
    });
    render();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
