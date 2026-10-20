# Deadline Repository — Moon Studio

Extensions et personnalisations du repository **AWS Thinkbox Deadline** utilisées par Moon Studio pour soumettre, exécuter et diagnostiquer les rendus Blender, Houdini et Redshift USD.

Ce dépôt n'est pas une installation complète de Deadline. Il contient uniquement un overlay `custom/` destiné à être intégré à la racine d'un repository Deadline existant.

## Fonctionnalités

- plugin Blender personnalisé : sélection de version, rendu GPU, contrôle des fichiers manquants et configuration OCIO ;
- plugin Houdini personnalisé : choix de build, intégration ToTheMoon, gestion de `MOON_PROJECT`, path mapping et détection d'erreurs Karma/Redshift ;
- plugin autonome `RedshiftUSD` pour rendre des scènes USD avec `redshiftUsdCmdLine` ;
- submitters Blender et Houdini utilisables depuis les DCC ;
- formulaires de soumission Blender et Redshift USD dans Deadline Monitor ;
- outils d'export des informations de jobs et de tâches en CSV ou JSON ;
- export des statistiques globales de la ferme en CSV.

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

Les fichiers `.param` décrivent la configuration d'un plugin dans Deadline, les fichiers `.options` les propriétés affichées sur les jobs, et les fichiers `.py` contiennent l'exécution ou la soumission.

## Installation

> Les dossiers `custom/plugins/Blender` et `custom/plugins/Houdini` remplacent les personnalisations portant le même nom dans le repository cible. Sauvegardez l'existant et validez d'abord le déploiement sur une ferme de test.

1. Cloner ce dépôt sur une machine ayant accès en écriture au repository Deadline.
2. Copier le **contenu** de `custom/` dans le dossier `custom/` du repository Deadline cible en conservant l'arborescence. Vous pouvez utiliser le Deadline repository de SRV-LICENCE pour effectuer des tests
3. Vérifier les chemins des exécutables depuis **Deadline Monitor > Tools > Configure Plugins**.
4. Installer ou mettre à jour les points d'entrée Blender/Houdini sur les postes artistes selon la procédure d'intégration DCC de votre installation Deadline.
5. Redémarrer les Workers concernés et relancer Deadline Monitor afin de recharger les plugins et scripts.
6. Soumettre un job court sur un Worker de test, puis contrôler le log, les images produites et le path mapping.

Une fois l'overlay chargé, les scripts rangés dans `scripts/Submission`, `scripts/Jobs`, `scripts/Tasks` et `scripts/General` apparaissent dans les menus correspondants de Deadline Monitor selon les droits de l'utilisateur.

## Configuration studio à vérifier

Cette version contient des valeurs spécifiques à l'infrastructure Moon Studio. Elles doivent être accessibles ou adaptées avant un déploiement dans un autre environnement :

- partages réseau `//10.0.1.32/moon_library/...` utilisés par Blender et Houdini ;
- configurations OCIO et scripts Blender présents sur ce partage ;
- code ToTheMoon importable par le plugin Houdini ;
- chemin des bibliothèques Python Deadline du studio ;
- conventions de chemins permettant de déduire `MOON_PROJECT` depuis la scène ;
- installations Windows de Blender et Houdini attendues par les plugins.

Le plugin Blender construit actuellement le chemin de l'exécutable à partir de la version soumise. Le plugin Houdini recherche le build exact demandé puis, si nécessaire, le build installé le plus récent de la même version majeure/mineure. Les valeurs déclarées dans les fichiers `.param` ne suffisent donc pas à décrire tout le comportement : relisez les méthodes `RenderExecutable` avant de changer la stratégie d'installation des DCC.

### Exports

- `Jobs/ExportJobInfo10_GUI.py` exporte les jobs sélectionnés et, au choix, leurs tâches en CSV ou JSON ;
- `Tasks/ExportJobInfoN_CSV.py` exporte les tâches sélectionnées vers `DeadlineTaskInfo.csv` sur le Bureau ;
- `General/farm_stats_csv.py` calcule les statistiques des jobs et écrit `jobs.csv` dans son dossier.

