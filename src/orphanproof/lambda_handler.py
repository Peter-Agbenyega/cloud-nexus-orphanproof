"""AWS Lambda entry point for the OrphanProof FastAPI application."""

from __future__ import annotations

from mangum import Mangum

from orphanproof.api import app

handler = Mangum(app)
