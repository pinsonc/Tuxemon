# direction => vector
dirs3 = {
    "up": Vector3(0, -1, 0),
    "down": Vector3(0, 1, 0),
    "left": Vector3(-1, 0, 0),
    "right": Vector3(1, 0, 0),
}
dirs2 = {
    "up": Vector2(0, -1),
    "down": Vector2(0, 1),
    "left": Vector2(-1, 0),
    "right": Vector2(1, 0),
}
# just the first letter of the direction => vector
short_dirs = {d[0]: dirs2[d] for d in dirs2}

# complimentary directions
pairs = {
    "up": "down",
    "down": "up",
    "left": "right",
    "right": "left"
}

# what directions entities can face
facing = "front", "back", "left", "right"


def translate_short_path(path, position=(0, 0)):
    """ Translate condensed path strings into coordinate pairs

    Uses a string of U D L R characters; Up Down Left Right.
    Passing a position will make the path relative to that point.

    :param path: string of path directions; ie "uldr"
    :type path: str
    :param position: starting point of the path

    :return: list
    """
    position = Point2(*position)
    for char in path.lower():
        position += short_dirs[char]
        yield position


def get_direction(base, target):
    y_offset = base[1] - target[1]
    x_offset = base[0] - target[0]
    # Is it further away vertically or horizontally?
    look_on_y_axis = abs(y_offset) >= abs(x_offset)

    if look_on_y_axis:
        return "up" if y_offset > 0 else "down"
    else:
        return "left" if x_offset > 0 else "right"


def proj(point):
    """ Project 3d coordinates to 2d.

    Not necessarily for use on a screen.

    :param point:

    :return: tuple
    """
    try:
        return Point2(point.x, point.y)
    except AttributeError:
        return point[0], point[1]


class PathfindNode(object):
    """ Used in path finding search
    """

    def __init__(self, value, parent=None):
        self.parent = parent
        self.value = value
        if self.parent:
            self.depth = self.parent.depth + 1
        else:
            self.depth = 0

    def get_parent(self):
        return self.parent

    def set_parent(self, parent):
        self.parent = parent
        self.depth = parent.depth + 1

    def get_value(self):
        return self.value

    def get_depth(self):
        return self.depth

    def __str__(self):
        s = str(self.value)
        if self.parent is not None:
            s += str(self.parent)
        return s


class Tile(object):
    """A class to create tile objects. Tile objects are used to keep track of tile properties such
    as the layer it's on, its position, surface, and other properties.

    """

    def __init__(self, name, surface, tileset):
        self.name = name
        self.surface = surface
        self.layer = None
        self.type = None
        self.tileset = tileset


class Map(object):
    """
    needs new name.  this handles the entities, actions and map of a single map
    """
    def __init__(self):
        # Collision lines (player can walk in tiles, but cannot cross
        # from one to another) Items in this list should be in the
        # form of pairs, signifying that it is NOT possible to travel
        # from the first tile to the second (but reverse may be
        # possible, i.e. jumping) All pairs of tiles must be adjacent
        # (not diagonal)
        self.events = list()
        self.inits = list()
        self.interacts = list()
        self.npcs = dict()
        # Create a map of all tiles that we cannot walk through
        self.collision_map = dict()
        # Create a list of all pairs of adjacent tiles that are impassable (aka walls)
        # example: ((5,4),(5,3), both)
        self.collision_lines_map = dict()

    def broadcast_player_teleport_change(self):
        """ Tell clients/host that player has moved or changed map after teleport

        :return:
        """
        # Set the transition variable in event_data to false when we're done
        self.game.event_data["transition"] = False

        # Update the server/clients of our new map and populate any other players.
        if self.game.isclient or self.game.ishost:
            self.game.add_clients_to_map(self.game.client.client.registry)
            self.game.client.update_player(self.player1.facing)

        # Update the location of the npcs. Doesn't send network data.
        for npc in self.npcs.values():
            char_dict = {"tile_pos": npc.tile_pos}
            networking.update_client(npc, char_dict, self.game)

        for npc in self.npcs_off_map.values():
            char_dict = {"tile_pos": npc.tile_pos}
            networking.update_client(npc, char_dict, self.game)

    ####################################################
    #            Pathfinding and Collisions            #
    ####################################################
    """
    eventually refactor pathing/collisions into a more generic class
    so it doesn't rely on a running game, players, or a screen
    """

    def add_player(self, player):
        """ WIP.  Eventually handle players coming and going (for server)

        :param player:
        :return:
        """
        self.player1 = player
        self.add_entity(player)

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

    def get_collision_map(self):
        """ Return dictionary for collision testing

        Returns a dictionary where keys are (x, y) tile tuples
        and the values are tiles or NPCs.

        # NOTE:
        This will not respect map changes to collisions
        after the map has been loaded!

        :rtype: dict
        :returns: A dictionary of collision tiles
        """
        # TODO: overlapping tiles/objects by returning a list
        collision_dict = dict()

        # Get all the NPCs' tile positions
        for npc in self.get_all_entities():
            pos = nearest(npc.tile_pos)
            collision_dict[pos] = {"entity": npc}

        # tile layout takes precedence
        collision_dict.update(self.collision_map)

        return collision_dict

    def pathfind(self, start, dest):
        """ Pathfind

        :param start:
        :type dest: tuple

        :return:
        """
        pathnode = self.pathfind_r(
            dest,
            [PathfindNode(start)],
            set(),
        )

        if pathnode:
            # traverse the node to get the path
            path = []
            while pathnode:
                path.append(pathnode.get_value())
                pathnode = pathnode.get_parent()

            return path[:-1]

        else:
            # TODO: get current map name for a more useful error
            logger.error("Pathfinding failed to find a path from " +
                         str(start) + " to " + str(dest) +
                         ". Are you sure that an obstacle-free path exists?")

    def pathfind_r(self, dest, queue, known_nodes):
        """ Breadth first search algorithm

        :type dest: tuple
        :type queue: list
        :type known_nodes: set

        :rtype: list
        """
        # The collisions shouldn't have changed whilst we were calculating,
        # so it saves time to reuse the map.
        collision_map = self.get_collision_map()
        while queue:
            node = queue.pop(0)
            if node.get_value() == dest:
                return node
            else:
                for adj_pos in self.get_exits(node.get_value(), collision_map, known_nodes):
                    new_node = PathfindNode(adj_pos, node)
                    known_nodes.add(new_node.get_value())
                    queue.append(new_node)

    def get_explicit_tile_exits(self, position, tile, skip_nodes):
        """ Check for exits from tile which are defined in the map

        This will return exits which were defined by the map creator

        Checks "continue" and "exits" properties of the tile

        :param position: tuple
        :param tile:
        :param skip_nodes: set
        :return: list
        """
        # Check if the players current position has any exit limitations.
        # this check is for tiles which define the only way to exit.
        # for instance, one-way tiles.

        # does the tile define continue movements?
        try:
            return [tuple(dirs2[tile['continue']] + position)]
        except KeyError:
            pass

        # does the tile explicitly define exits?
        try:
            adjacent_tiles = list()
            for direction in tile["exit"]:
                exit_tile = tuple(dirs2[direction] + position)
                if exit_tile in skip_nodes:
                    continue

                adjacent_tiles.append(exit_tile)
            return adjacent_tiles
        except KeyError:
            pass

    def get_exits(self, position, collision_map=None, skip_nodes=None):
        """ Return list of tiles which can be moved into

        This checks for adjacent tiles while checking for walls,
        npcs, and collision lines, one-way tiles, etc

        :param position: tuple
        :param collision_map: dict
        :param skip_nodes: set

        :rtype: list
        """
        # get tile-level and npc/entity blockers
        if collision_map is None:
            collision_map = self.get_collision_map()

        if skip_nodes is None:
            skip_nodes = set()

        # if there are explicit way to exit this position use that
        # information only and do not check surrounding tiles.
        # handles 'continue' and 'exits'
        tile_data = collision_map.get(position)
        if tile_data:
            exits = self.get_explicit_tile_exits(position, tile_data, skip_nodes)
            if exits:
                return exits

        # get exits by checking surrounding tiles
        adjacent_tiles = list()
        for direction, neighbor in (
                ("down", (position[0], position[1] + 1)),
                ("right", (position[0] + 1, position[1])),
                ("up", (position[0], position[1] - 1)),
                ("left", (position[0] - 1, position[1])),
        ):
            if neighbor in skip_nodes:
                continue

            # We only need to check the perimeter,
            # as there is no way to get further out of bounds
            if position[0] in self.invalid_x or position[1] in self.invalid_y:
                continue

            # check to see if this tile is separated by a wall
            if (position, direction) in self.collision_lines_map:
                # there is a wall so stop checking this direction
                continue

            # test if this tile has special movement handling
            # NOTE: Do not refact. into a dict.get(xxxxx, None) style check
            # NOTE: None has special meaning in this check
            try:
                tile_data = collision_map[neighbor]
            except KeyError:
                pass
            else:
                # None means tile is blocked with no specific data
                if tile_data is None:
                    continue

                try:
                    if pairs[direction] not in tile_data['enter']:
                        continue
                except KeyError:
                    continue

            # no tile data, so assume it is free to move into
            adjacent_tiles.append(neighbor)

        return adjacent_tiles

    def get_pos_from_tilepos(self, tile_position):
        """ Returns the map pixel coordinate based on tile position.

        USE this to draw to the screen

        :param tile_position: An [x, y] tile position.

        :type tile_position: List

        :rtype: List
        :returns: The pixel coordinates to draw at the given tile position.
        """
        cx, cy = self.current_map.renderer.get_center_offset()
        px, py = self.project(tile_position)
        x = px + cx
        y = py + cy
        return x, y

    def move_npcs(self, time_delta):
        """ Move NPCs and Players around according to their state

        :type time_delta: float
        :return:
        """
        # TODO: This function may be moved to a server
        # Draw any game NPC's
        for entity in self.get_all_entities():
            entity.move(time_delta)

            if entity.update_location:
                char_dict = {"tile_pos": entity.final_move_dest}
                networking.update_client(entity, char_dict, self.game)
                entity.update_location = False

        # Move any multiplayer characters that are off map so we know where they should be when we change maps.
        for entity in self.npcs_off_map.values():
            entity.move(time_delta, self)

    def _collision_box_to_pgrect(self, box):
        """Returns a pygame.Rect (in screen-coords) version of a collision box (in world-coords).
        """

        # For readability
        x, y = self.get_pos_from_tilepos(box)
        tw, th = self.tile_size

        return pygame.Rect(x, y, tw, th)

    def _npc_to_pgrect(self, npc):
        """Returns a pygame.Rect (in screen-coords) version of an NPC's bounding box.
        """
        pos = self.get_pos_from_tilepos(npc.tile_pos)
        return pygame.Rect(pos, self.tile_size)

    def load_map(self, map_name):
        """ Returns map data as a dictionary to be used for map changing and preloading
        """
        map_data = {}
        map_data["data"] = Map(map_name)
        map_data["events"] = map_data["data"].events
        map_data["inits"] = map_data["data"].inits
        map_data["interacts"] = map_data["data"].interacts
        map_data["collision_map"]
        map_data["collision_lines_map"]
        map_data["map_size"] = \
            map_data["data"].loadfile()
