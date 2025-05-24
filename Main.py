import sys
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = "MTMzNjM1MjYzMjc3MTcwNjk2NQ.GW9oBY.xnxx3Fdef4zRcY8zA5MHYkxehEE5opr3uOrSDc"  # Replace with your bot token
STAFF_CHANNEL_ID = 1016836402178170970  # Your staff channel ID

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

application_systems = {}  # guild_id: {"channel_id": int, "questions": list[str]}

# Modal to collect up to 5 questions from admin
class QuestionSetupModal(discord.ui.Modal, title="Set Application Questions"):
    q1 = discord.ui.TextInput(label="Question 1", required=False, max_length=200)
    q2 = discord.ui.TextInput(label="Question 2", required=False, max_length=200)
    q3 = discord.ui.TextInput(label="Question 3", required=False, max_length=200)
    q4 = discord.ui.TextInput(label="Question 4", required=False, max_length=200)
    q5 = discord.ui.TextInput(label="Question 5", required=False, max_length=200)

    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction):
        questions = [q for q in [self.q1.value, self.q2.value, self.q3.value, self.q4.value, self.q5.value] if q.strip()]
        if not questions:
            await interaction.response.send_message("❌ You must provide at least one question.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        application_systems[guild_id] = {
            "channel_id": self.target_channel.id,
            "questions": questions
        }

        embed = discord.Embed(
            title="📋 Application System Created",
            description=f"Application with {len(questions)} questions created.\nClick the button below to start the application.",
            color=discord.Color.blurple()
        )

        class StartApplicationView(discord.ui.View):
            def __init__(self, guild_id):
                super().__init__(timeout=None)
                self.guild_id = guild_id

            @discord.ui.button(label="Start Application", style=discord.ButtonStyle.primary, custom_id="start_application")
            async def start_application(self, interaction: discord.Interaction, button: discord.ui.Button):
                system = application_systems.get(self.guild_id)
                if not system:
                    await interaction.response.send_message("❌ Application system not found.", ephemeral=True)
                    return

                class ApplicationModal(discord.ui.Modal, title="Application Form"):
                    def __init__(self, questions):
                        super().__init__()
                        self.questions = questions
                        for i, q in enumerate(questions):
                            self.add_item(discord.ui.TextInput(label=f"Q{i+1}: {q}", style=discord.TextStyle.paragraph, required=True, max_length=1000))

                    async def on_submit(self2, modal_interaction: discord.Interaction):
                        answers = [item.value for item in self2.children]
                        staff_channel = bot.get_channel(STAFF_CHANNEL_ID)
                        if staff_channel:
                            embed = discord.Embed(title="New Application Submitted", color=discord.Color.green())
                            embed.set_author(name=modal_interaction.user.name, icon_url=modal_interaction.user.display_avatar.url)
                            for i, (question, answer) in enumerate(zip(self2.questions, answers), start=1):
                                embed.add_field(name=f"Q{i}: {question}", value=answer or "No answer", inline=False)
                            await staff_channel.send(embed=embed)
                        await modal_interaction.response.send_message("✅ Your application has been submitted. Thank you!", ephemeral=True)

                await interaction.response.send_modal(ApplicationModal(system["questions"]))

        view = StartApplicationView(guild_id)
        await self.target_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Application system created in {self.target_channel.mention}!", ephemeral=True)


@bot.tree.command(name="create_application", description="Create an application system in a specific channel.")
@app_commands.describe(channel="The channel where the application system will be posted.")
async def create_application(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_modal(QuestionSetupModal(channel))


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Sync failed: {e}")
    print(f"🤖 Logged in as {bot.user}")


def run_bot():
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_bot()
