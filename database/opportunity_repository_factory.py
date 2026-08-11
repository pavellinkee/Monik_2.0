"""
Opportunity repository factory.

Responsibility:
    Construct the opportunity repository using the existing
    database infrastructure.
"""

from __future__ import annotations

from database.opportunity_database_adapter import (
    OpportunityDatabaseAdapter,
)
from database.opportunity_repository import (
    SqlOpportunityRepository,
)


class OpportunityRepositoryFactory:
    """
    Creates the SQL opportunity repository.
    """

    def create(
        self,
        database,
    ) -> SqlOpportunityRepository:
        """
        Build a repository around the supplied database.
        """

        adapter = OpportunityDatabaseAdapter(
            database
        )

        return SqlOpportunityRepository(
            adapter
        )

    def build(
        self,
        database,
    ) -> SqlOpportunityRepository:
        """
        Compatibility alias.
        """

        return self.create(
            database
        )
