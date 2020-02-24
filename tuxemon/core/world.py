import logging

logger = logging.getLogger(__name__)


class World(object):
    """

    contains maps, entities, variables, event handler, and scheduler

    """

    def __init__(self):
        self.entities = None
        self.npcs = dict()

    def add_entity(self, entity):
        """

        :type entity: core.entity.Entity
        :return:
        """
        entity.world = self
        self.npcs[entity.slug] = entity

    def get_entity(self, slug):
        """

        :type slug: str
        :return:
        """
        return self.npcs.get(slug)

    def remove_entity(self, slug):
        """

        :type slug: str
        :return:
        """
        del self.npcs[slug]

    def get_all_entities(self):
        """ List of players and NPCs, for collision checking

        :return:
        """
        return self.npcs.values()

    def get_all_entities_on_map(self, map_name):
        """

        :param map_name:
        :return:
        """
        # TODO: filter by map
        return self.npcs.values()

    def move_npcs(self, time_delta):
        """ Move NPCs and Players around according to their state

        :type time_delta: float
        :return:
        """
        # TODO: This function may be moved to a server
        # Draw any game NPC's
        for entity in self.get_all_entities():
            entity.move(time_delta)

            # if entity.update_location:
            #     char_dict = {"tile_pos": entity.final_move_dest}
            #     networking.update_client(entity, char_dict, self.game)
            #     entity.update_location = False

    ####################################################
    #             Map Change/Load Functions            #
    ####################################################
    def change_map(self, map_name):
        # Set the currently loaded map. This is needed because the event
        # engine loads event conditions and event actions from the currently
        # loaded map. If we change maps, we need to update this.
        if map_name not in self.preloaded_maps.keys():
            logger.debug("Map was not preloaded. Loading from disk.")
            map_data = self.load_map(map_name)
        else:
            logger.debug("%s was found in preloaded maps." % map_name)
            map_data = self.preloaded_maps[map_name]
            self.clear_preloaded_maps()

        self.current_map = map_data["data"]
        self.collision_map = map_data["collision_map"]
        self.collision_lines_map = map_data["collision_lines_map"]
        self.map_size = map_data["map_size"]

        # The first coordinates that are out of bounds.
        self.invalid_x = (-1, self.map_size[0] + 1)
        self.invalid_y = (-1, self.map_size[1] + 1)

        # TODO: remove this monkey [patching!] business for the main control/game
        self.game.events = map_data["events"]
        self.game.inits = map_data["inits"]
        self.game.interacts = map_data["interacts"]
        self.game.event_engine.reset()
        self.game.event_engine.current_map = map_data
