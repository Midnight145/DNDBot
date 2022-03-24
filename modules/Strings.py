def announcement_message(name: str):
    return __ANNOUNCEMENT_MESSAGE.format(name=name)


def verification_denied(channel):
    return __VERIFICATION_DENIED.format(channel=channel)


INFO_MESSAGE = ("Here is where the Dungeon Master can post important information regarding the campaign that players "
                "may need to refer back to. This information can include a description of the **location** the "
                "campaign takes place in, the **mission** the players are taking on, and a **map** of the land.")

NOTES_MESSAGE = ("This is where players and the DM can post notes that they want to remember. Meet an important "
                 "character? Write it down! Don't wanna forget a tidbit of information a character gave you? Write it "
                 "down! Keep in mind the DM may ask you not to write down notes if they choose to.")

PICS_MESSAGE = ("This is where anyone can post pictures of their characters, locations, etc. Be sure to label it so "
                "you can refer back to it later! ")

__ANNOUNCEMENT_MESSAGE = ("Welcome to the **{name}** campaign category! This is where your Dungeon Master can post "
                          "announcements, information, and other important information regarding the campaign. "
                          "Players and the DM may also communicate in #lobby. If your sessions are virtual, "
                          "they will be held through this category's voice channel. Let me know if you have any "
                          "questions, and have fun!")

__VERIFICATION_DENIED = ("Your verification has been denied due to your nickname not following the instructions as "
                         "described in <#{channel}>. If you believe this to be a mistake, please contact the "
                         "President.")
