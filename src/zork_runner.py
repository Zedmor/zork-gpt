from time import sleep
from asyncio.subprocess import PIPE
import asyncio

from chatgpt_wrapper import OpenAIAPI
from chatgpt_wrapper.backends.openai.database import Database
from chatgpt_wrapper.backends.openai.user import UserManager
from chatgpt_wrapper.core.config import Config

config = Config()
config.set('database', 'sqlite:///storage.db')
config.set('chat.model', 'gpt4')

manager = UserManager(config)
database = Database(config)
# database.create_schema()
# manager.register("zedmor", email="zedmor@zzz.ccc", password="abc12345")

gpt = OpenAIAPI(config)
gpt.set_current_user(manager.get_by_username_or_email(identifier="zedmor")[1])

prompt = """
You are AdventureSolverGPT. You are trying to solve text adventure game, you will get
         promts and you should answer only as input to the adventure game, then you will get
         next
         prompt etc. Your goal is to solve the game. 

Communicating with Interactive Fiction

(If you are not familiar with Interactive
Fiction, please read this section.)

With Interactive Fiction, you type your
commands in plain English each time you see
the prompt (>). Most of the sentences that
The STORIES will understand are imperative
sentences. See the examples below. When
you have finished typing your input, press the
RETURN (or ENTER) key. The STORY will
then respond, telling you whether your
request is possible at this point in the story,
and what happened as a result.
To move around, just type the direction you
want to go. Directions can be abbreviated:
NORTH to N, SOUTH to S, EAST to E,
WEST to W, NORTHEAST to NE,
NORTHWEST to NW, SOUTHEAST to SE,
SOUTHWEST to SW, UP to U, and DOWN 
to D. IN and OUT will also work in certain
places.
There are many different kinds of sentences
used in interactive fiction games. Here
are some examples:
>WALK TO THE NORTH
>WEST
>NE
>DOWN
>TAKE THE BIRDCAGE
>OPEN THE PANEL
>READ ABOUT DIMWIT FLATHEAD
>HIT THE LAMP
>LIE DOWN IN THE PINK SOFA
>EXAMINE THE SHINY COIN
>PUT THE RUSTY KEY IN THE
CARDBOARD BOX
>SHOW MY BOW TIE TO THE
BOUNCER
>HIT THE CRAWLING CRAB WITH THE
GIANT NUTCRACKER
>ASK THE COWARDLY KING ABOUT
THE CROWN JEWELS
You can use multiple objects with certain
verbs if you separate them by the word AND
or by a comma. Some examples:
>TAKE THE BOOK AND THE FROG
>DROP THE JAR OF PEANUT BUTTER,
THE SPOON, AND THE LEMMING FOOD
>PUT THE EGG AND THE PENCIL IN
THE CABINET
You can include several inputs on one line if
you separate them by the word THEN or
by a period. Each input will handled in order,
as though you had typed them individually at
separate prompts. For example, you could
type all of the following at once, before
pressing the RETURN (or ENTER) key:
>TURN ON THE LIGHT. KICK THE
LAMP.
If The STORY doesn't understand one of the
sentences on your input line, or if an unusual
event occurs, it will ignore the rest of your
input line. The words IT and ALL can be very
useful. For example:
>EXAMINE THE APPLE. TAKE IT. EAT
IT
>CLOSE THE HEAVY METAL DOOR.
LOCK IT
>PICK UP THE GREEN Boor. SMELL IT.
PUT IT ON.
>TAKE ALL
>TAKE ALL THE TOOLS
>DROP ALL THE TOOLS EXCEPT THE
WRENCH AND THE MINIATURE
HAMMER
>TAKE ALL FROM THE CARTON
>GIVE ALL BUT THE RUBY SLIPPERS
TO THE WICKED WITCH
The word ALL refers to every visible object
except those inside something else. If there
were an apple on the ground and an orange
inside a cabinet, TAKE ALL would take
the apple but not the orange.
When you meet intelligent creatures, you can
talk to them by typing their name, then
a comma, then whatever you want to say to
them. Here are some examples:
>SALESMAN, HELLO
>HORSE, WHERE IS YOUR SADDLE?
>BOY, RUN HOME THEN CALL THE
POLICE
>MIGHTY WIZARD, TAKE THIS
POISONED APPLE. EAT IT
Notice that in the last two examples, you are
giving the character more than one command
on the same input line. Keep in mind,
however, that many creatures don't care for 
idle chatter; your actions will speak louder
than your words.
Basic Commands
BRIEF - This command fully describe a
location only the first time you enter it. On
subsequent visits, only the name of the
location and any objects present will be
described. The adventures will begin in
BRIEF mode, and remain in BRIEF mode
unless you use the VERBOSE or
SUPERBRIEF commands SUPERBRIEF
displays only the name of a place you have
entered, even if you have never been there
before. In this mode, not even mention
objects are described. Of course, you can
always get a full description of your location
and the items there by typing LOOK. In
SUPERBRIEF mode, the blank line between
turns will be eliminated. This mode is meant
for players who are already familiar with the
geography. The VERBOSE command gives a
complete description of each location, and the
objects in it, every time you enter a location,
even if you've been there before.
DIAGNOSE - This will give you a report of
your physical condition.
INVENTORY - This will give you a list
what you are carrying and wearing. You can
abbreviate INVENTORY to I.
LOOK - This will give you a full description
of your location. You can abbreviate
LOOK to L.
EXAMINE object - This will give you a
description of the object. It is important
to look at all objects as there may be clues to
an object's use in its description. You can
abbreviate EXAMINE to X.
QUIT - This lets you stop. If you want to
save your position before quitting, you must
use the SAVE command.
RESTORE - This restores a previously saved
position.
RESTART - This stops the story and starts it
over from the beginning.
SAVE - This saves a "snapshot" of your
current position. You can return to a saved
position in the future using the RESTORE
command.
WAIT - Allows time to pass; effectively you
do nothing while the game continues. You
can abbreviate WAIT to Z.
SCORE - Displays your current score and
rank. Typing FULL SCORE will show you
what you have done to earn your points.
"""

gpt.set_model_system_message(prompt)


async def handle_stdout(stdout, callback):
    # This coroutine reads lines from the process's standard output and puts them in a queue.
    while True:
        line = ""
        while not line.endswith(">"):
            char = await stdout.read(1)  # read a single character from stdout
            if not char:  # if the character is empty, the process has exited
                break
            line += char.decode()

        if not line:  # if the line is empty, the process has exited
            break
        await callback(line.strip())  # add the line to the queue, waiting if necessary


async def handle_stdin(stdin, queue):
    # This coroutine reads data from a queue and sends it to the process's standard input.
    while True:
        data = await queue.get()  # wait for data to be available in the queue
        if not data:  # if the data is empty, we're done
            break
        stdin.write(data.encode() + b"\n")  # write the data to stdin, with a newline
        await stdin.drain()  # make sure the write is complete before continuing


async def interact_with_command(command, gpt):
    # This coroutine interacts with the given command using the given GPT object.
    process = await asyncio.create_subprocess_shell(
        command,
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE
        )

    # Start the coroutine to handle stdout in a separate task.
    stdout_queue = asyncio.Queue()
    asyncio.ensure_future(handle_stdout(process.stdout, stdout_queue.put))
    process.stdin.write(b'\n')


    # Read input from the user and feed it to the GPT object.

    while True:
        line = await stdout_queue.get()
        print(f"IF: {line}")
        assert line.endswith('>')
        line = line[:-1]
        success, response, message = gpt.ask(line.strip())
        sleep(3)
        if success:
            # Send the response back to the command.
            print(f"GPT4: {response}")
            process.stdin.write(response.encode() + b"\n")
            # await process.stdin.drain()

        else:
            # If the GPT object returned an error, print it and exit the loop.
            print(f"GPT error: {message}")
            break

    # Stop the subprocess and exit.
    process.terminate()
    await process.wait()


async def main():
    # Create a GPT object and start the coroutine to interact with the command.
    await interact_with_command("/usr/games/dfrotz ~/Downloads/sherlock-nosound-r4-s880324.z5 -p", gpt)


asyncio.run(main())
