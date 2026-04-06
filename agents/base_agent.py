# agents/base_agent.py
"""
BaseAgent — classe de base abstraite pour tous les agents spécialistes Resilio+.

Interface publique :
    agent_type : AgentType  (attribut de classe)
    prescribe(view: dict) -> dict   (à implémenter — reçoit la vue filtrée)
    run(state) -> dict              (appelé par le Head Coach)

Flux d'appel Head Coach :
    node_delegate_to_agents → agent.run(state) → get_agent_view() → prescribe()
"""

from abc import ABC, abstractmethod

from models.schemas import AthleteStateSchema
from models.views import AgentType, get_agent_view


class BaseAgent(ABC):
    """Classe de base pour tous les agents spécialistes."""

    agent_type: AgentType

    @abstractmethod
    def prescribe(self, view: dict) -> dict:
        """
        Prescrit un plan partiel à partir de la vue filtrée de l'agent.

        Args:
            view: dict filtré par get_agent_view() — contient uniquement
                  les données pertinentes à cet agent.

        Returns:
            dict avec au minimum {"sessions": [], "agent": "<type>", "notes": ""}
        """

    def run(self, state: AthleteStateSchema) -> dict:
        """
        Appelé par le Head Coach. Extrait la vue filtrée et appelle prescribe().

        Args:
            state: AthleteState complet — seule la vue filtrée est transmise à prescribe()

        Returns:
            Plan partiel retourné par prescribe()
        """
        view = get_agent_view(state, self.agent_type)
        return self.prescribe(view)
