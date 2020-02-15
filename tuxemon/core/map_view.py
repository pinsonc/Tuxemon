class MapView(object):

    def initialize_renderer(self):
        """ Initialize the renderer for the map and sprites

        :rtype: pyscroll.BufferedRenderer
        """
        # TODO: Use self.edges == "stitched" here when implementing seamless maps
        visual_data = pyscroll.data.TiledMapData(self.data)
        clamp = (self.edges == "clamped")
        return pyscroll.BufferedRenderer(visual_data, prepare.SCREEN_SIZE, clamp_camera=clamp, tall_sprites=2)

    def load(self):
        # Scale the loaded tiles if enabled
        if prepare.CONFIG.scaling:
            self.data = pytmx.TiledMap(filename,
                                       image_loader=scaled_image_loader,
                                       pixelalpha=True)
            self.data.tilewidth, self.data.tileheight = prepare.TILE_SIZE
        else:
            self.data = load_pygame(filename, pixelalpha=True)

    def draw(self, surface):
        # TODO: move all drawing into a "WorldView" widget
        # interlace player sprites with tiles surfaces.
        # eventually, maybe use pygame sprites or something similar
        world_surfaces = list()

        # get player coords to center map
        cx, cy = nearest(self.project(self.player1.tile_pos))

        # offset center point for player sprite
        cx += prepare.TILE_SIZE[0] // 2
        cy += prepare.TILE_SIZE[1] // 2

        # center the map on center of player sprite
        # must center map before getting sprite coordinates
        self.current_map.renderer.center((cx, cy))

        # get npc surfaces/sprites
        for npc in self.npcs:
            world_surfaces.extend(self.npcs[npc].get_sprites())

        # get map_animations
        for anim_data in self.map_animations.values():
            anim = anim_data['animation']
            if not anim.isFinished() and anim.visibility:
                frame = (anim.getCurrentFrame(), anim_data["position"], anim_data['layer'])
                world_surfaces.append(frame)

        # position the surfaces correctly
        # pyscroll expects surfaces in screen coords, so they are
        # converted from world to screen coords here
        screen_surfaces = list()
        for frame in world_surfaces:
            s, c, l = frame

            # project to pixel/screen coords
            c = self.get_pos_from_tilepos(c)

            # TODO: better handling of tall sprites
            # handle tall sprites
            h = s.get_height()
            if h > prepare.TILE_SIZE[1]:
                # offset for center and image height
                c = nearest((c[0], c[1] - h // 2))

            screen_surfaces.append((s, c, l))

        # draw the map and sprites
        self.rect = self.current_map.renderer.draw(surface, surface.get_rect(), screen_surfaces)

        # If we want to draw the collision map for debug purposes
        if prepare.CONFIG.collision_map:
            self.debug_drawing(surface)


