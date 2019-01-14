# encoding:utf-8
from fb_parse.FB_parser import FB_parser

fb_groups = [
    'https://www.facebook.com/groups/673389662794979/', # Boston Housing, Rooms, Apartments, Sublets
    'https://www.facebook.com/groups/1210575355774169/', # Boston & Cambridge Apartments, Housing, Sublets & Rooms
    'https://www.facebook.com/groups/735597296550141/', # Harvard University Housing, Sublets & Roommates
]

for group in fb_groups:
    fb_parser = FB_parser(group)
    fb_parser.process_group()