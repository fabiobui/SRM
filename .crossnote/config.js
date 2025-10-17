({
  katexConfig: {
  "macros": {}
},
  
  mathjaxConfig: {
  "tex": {},
  "options": {},
  "loader": {}
},
  
  mermaidConfig: {
  "startOnLoad": false
},

  export: {
    pdf: {
      converter: "pandoc",   // 👈 usa pandoc invece di ebook-convert
      path: "./exports",     // (opzionale) cartella dove salvare i PDF
      toc: true,             // (opzionale) aggiunge Table of Contents
      latexEngine: "xelatex" // (opzionale) migliore compatibilità con Unicode
    }
  }
})