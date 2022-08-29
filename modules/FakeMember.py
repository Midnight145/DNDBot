class FakeMember:
    def __init__(self, id):
        self.id = id
        self.roles = []
        self.mention = str(id) + " FakeMember"

    async def remove_roles(self, role):
        return

    async def add_roles(self, role):
        return