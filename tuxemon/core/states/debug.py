"""

WIP make a state that is responsible for printing/displaying debug info

"""
# TODO: move to its own state
# def draw_event_debug(self):
#     """ Very simple overlay of event data.  Needs some love.
#
#     :return:
#     """
#     y = 20
#     x = 4
#
#     yy = y
#     xx = x
#
#     font = pg.font.Font(pg.font.get_default_font(), 15)
#     for event in self.event_engine.partial_events:
#         w = 0
#         for valid, item in event:
#             p = ' '.join(item.parameters)
#             text = "{} {}: {}".format(item.operator, item.type, p)
#             if valid:
#                 color = (0, 255, 0)
#             else:
#                 color = (255, 0, 0)
#             image = font.render(text, 1, color)
#             self.screen.blit(image, (xx, yy))
#             ww, hh = image.get_size()
#             yy += hh
#             w = max(w, ww)
#
#         xx += w + 20
#
#         if xx > 1000:
#             xx = x
#             y += 200
#
#         yy = y
