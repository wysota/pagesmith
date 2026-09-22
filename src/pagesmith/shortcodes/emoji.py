"""Emoji shortcode for embedding emojis in text."""

import re


# Unicode emoji data: common emojis mapped by name
EMOJI_MAP = {
    # Smileys & emotions
    'smile': '😊',
    'smiley': '😄',
    'grin': '😁',
    'joy': '😂',
    'sunglasses': '😎',
    'wink': '😉',
    'blush': '😊',
    'heart_eyes': '😍',
    'thinking': '🤔',
    'hushed': '😮',
    'sob': '😭',
    'angry': '😠',
    'confused': '😕',
    'sweat_smile': '😅',
    
    # Hand gestures
    'thumbsup': '👍',
    'thumbsdown': '👎',
    'ok_hand': '👌',
    'punch': '👊',
    'fist': '✊',
    'wave': '👋',
    'raised_hand': '✋',
    'clap': '👏',
    'pray': '🙏',
    'point_right': '👉',
    'point_left': '👈',
    
    # Objects & symbols
    'rocket': '🚀',
    'fire': '🔥',
    'star': '⭐',
    'sparkles': '✨',
    'boom': '💥',
    'bulb': '💡',
    'gear': '⚙️',
    'wrench': '🔧',
    'hammer': '🔨',
    'lock': '🔒',
    'unlock': '🔓',
    'warning': '⚠️',
    'checkmark': '✅',
    'x': '❌',
    'stop': '🛑',
    'clock': '🕐',
    'calendar': '📅',
    'memo': '📝',
    'page': '📄',
    'chart': '📊',
    'mag': '🔍',
    'link': '🔗',
    
    # Nature & animals
    'sun': '☀️',
    'moon': '🌙',
    'cloud': '☁️',
    'umbrella': '☔',
    'snowflake': '❄️',
    'snowman': '⛄',
    'leaves': '🍃',
    'apple': '🍎',
    'banana': '🍌',
    'cake': '🍰',
    'coffee': '☕',
    'beer': '🍺',
    'wine': '🍷',
    
    # Travel & places
    'car': '🚗',
    'bus': '🚌',
    'airplane': '✈️',
    'house': '🏠',
    'office': '🏢',
    'school': '🏫',
    'hospital': '🏥',
    'bank': '🏦',
    'earth': '🌍',
    'globe': '🌐',
    
    # Tech
    'computer': '💻',
    'mobile': '📱',
    'keyboard': '⌨️',
    'mouse': '🖱️',
    'printer': '🖨️',
    'battery': '🔋',
    'electric_plug': '🔌',
    'dvd': '📀',
    'floppy': '💾',
    
    # People & relations
    'boy': '👦',
    'girl': '👧',
    'man': '👨',
    'woman': '👩',
    'baby': '👶',
    'grandpa': '👴',
    'grandma': '👵',
    'family': '👨‍👩‍👧‍👦',
    
    # Misc
    'heart': '❤️',
    'broken_heart': '💔',
    'yellow_heart': '💛',
    'blue_heart': '💙',
    'green_heart': '💚',
    'purple_heart': '💜',
    'gift': '🎁',
    'trophy': '🏆',
    'medal': '🏅',
    'ribbon': '🎀',
    'flag': '🚩',
    'tada': '🎉',
    'confetti': '🎊',
    'balloon': '🎈',
}


def emoji(args=None, kwargs=None, content=None):
    """Embeds an emoji by name.
    
    Usage:
        {% emoji 'rocket' %}           → 🚀
        {% emoji name='thumbsup' %}    → 👍
        {% emoji 🚀 %}                 → 🚀 (literal emoji)
    
    For a list of emoji names, see shortcodes/emoji.py EMOJI_MAP.
    """
    # First, check if a literal emoji was passed
    if args and args[0]:
        first_arg = args[0].strip()
        # Check if it's a literal emoji (Unicode character in specific ranges)
        if len(first_arg) <= 2 and is_emoji(first_arg):
            return first_arg
    
    # Otherwise, look up by name
    name = kwargs.get('name') or (args[0].strip() if args else '')
    name = name.lower().strip(':')  # Allow :name: syntax, strip colons
    
    if not name:
        return ''
    
    return EMOJI_MAP.get(name, '')


def is_emoji(s):
    """Check if a string contains an emoji."""
    # Simple check for common emoji ranges
    for char in s:
        code = ord(char)
        # Emoji ranges in Unicode
        if (
            (0x1F000 <= code <= 0x1F9FF) or  # Emoticons, symbols, pictographs (includes arrows, etc.)
            (0x2600 <= code <= 0x27BF) or    # Miscellaneous symbols and Dingbats
            (0x2300 <= code <= 0x23FF) or    # Miscellaneous technical
            (0x2B50 <= code <= 0x2B55)       # Star symbols
        ):
            return True
    return False


# Attach name property for auto-discovery
emoji.name = 'emoji'
