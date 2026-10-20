# Deadline Repository — Moon Studio

Extensions et personnalisations du repository **AWS Thinkbox Deadline** utilisées par Moon Studio pour soumettre, exécuter et diagnostiquer les rendus Blender, Houdini et Redshift USD.

Ce dépôtcontient uniquement un overlay `custom/`

## Fonctionnalités

- plugin Blender personnalisé : sélection de version, rendu GPU, contrôle des fichiers manquants et configuration OCIO ;
- plugin Houdini personnalisé : choix de build, intégration ToTheMoon, gestion de `MOON_PROJECT`, path mapping et détection d'erreurs Karma/Redshift ;
- plugin autonome `RedshiftUSD` pour rendre des scènes USD avec `redshiftUsdCmdLine` ;
- submitters Blender et Houdini utilisables depuis les DCC ;
- formulaires de soumission Blender et Redshift USD dans Deadline Monitor ;

## Arborescence

```text
custom/
├── plugins/
│   ├── Blender/       # Plugin de rendu Blender personnalisé
│   ├── Houdini/       # Plugin de rendu Houdini et script hrender_dl
│   └── RedshiftUSD/   # Plugin de rendu Redshift en ligne de commande
├── scripts/
│   ├── General/       # Statistiques globales de la ferme
│   ├── Jobs/          # Export interactif des jobs et de leurs tâches
│   ├── Submission/    # Formulaires de soumission du Monitor
│   └── Tasks/         # Export des tâches sélectionnées
└── submission/
    ├── Blender/Main/  # Point d'entrée exécuté depuis Blender
    └── Houdini/Main/  # Submitter Houdini et Deadline ROP
```

