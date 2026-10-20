"""QuantHub: project hosting, file management and experiments for quantum research.

The package name is ``quanthub`` and the product renders as **QuantHub**.

Storage contract
----------------
* SQLite (``config.db_path``) owns project metadata, permissions, experiment
  specifications and run metadata.
* Each project's files live in a bare Git repository under ``config.repos_dir``.
* Experiment evidence is written once by the scientific engine and never
  rewritten; see :mod:`app.quanthub.experiments`.
"""

__all__ = ["config", "db", "experiments", "news", "service"]
