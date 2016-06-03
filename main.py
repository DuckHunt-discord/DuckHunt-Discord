# -*- coding:Utf-8 -*-
# !/usr/bin/env python3.5
"""
Discord-duckhunt -- main.py
MODULE DESC 
"""
# Constants #
import random
import time

import database

__author__ = "Arthur — paris-ci"
__licence__ = "WTFPL — 2016"

print("Démarrage...")

import argparse

parser = argparse.ArgumentParser(description="DuckHunt, jeu pour tirer sur des canards, pour Discord")
parser.add_argument("-d", "--debug", help="Affiche les messages de débug", action="store_true")

args = parser.parse_args()

import logging
from logging.handlers import RotatingFileHandler

import sys
import discord
import asyncio

from config import *

## INIT ##
logger = logging.getLogger("duckhunt")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
file_handler = RotatingFileHandler('activity.log', 'a', 1000000, 1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
steam_handler = logging.StreamHandler()
if args.debug:
    steam_handler.setLevel(logging.DEBUG)
else:
    steam_handler.setLevel(logging.INFO)
logger.addHandler(steam_handler)
steam_handler.setFormatter(formatter)
logger.debug("Logger Initialisé")
logger.info("Initialisation du programme, merci de patienter...")
logger.debug("Version : " + str(sys.version))
client = discord.Client()

planification = {}  # {"channel":[time objects]}
canards = []  # [{"channel" : channel, "time" : time.time()}]


@asyncio.coroutine
def planifie():
    global planification

    planification_ = {}

    logger.debug("Time now : " + str(time.time()))

    for server in client.servers:
        logger.debug("Serveur " + str(server))
        for channel in server.channels:
            if channel.type == discord.ChannelType.text:

                logger.debug(" |- Check channel : " + channel.id + " | " + channel.name)
                permissions = channel.permissions_for(server.me)
                if permissions.read_messages and permissions.send_messages:
                    if (channelWL and int(channel.id) in whitelist) or not channelWL:

                        logger.debug("   |-Ajout channel : " + channel.id)
                        templist = []
                        now = time.time()
                        thisDay = now - (now % 86400)
                        for id in range(1, canardsJours + 1):
                            templist.append(int(thisDay + random.randint(0, 86400)))
                        planification_[channel] = sorted(templist)

    logger.debug("Nouvelle planification : " + str(planification_))

    logger.debug("Supression de l'ancienne planification, et application de la nouvelle")

    planification = planification_  # {"channel":[time objects]}


def nouveauCanard(canard):
    logger.debug("Nouveau canard : " + str(canard))
    yield from client.send_message(canard["channel"], "-,_,.-'`'°-,_,.-'`'° /_^<   QUAACK")
    canards.append(canard)


def getprochaincanard():
    now = time.time()
    prochaincanard = {"time": 0, "channel": None}
    for channel in planification.keys():  # Determination du prochain canard
        for canard in planification[channel]:
            if canard > now:
                if canard < prochaincanard["time"] or prochaincanard["time"] == 0:
                    prochaincanard = {"time": canard, "channel": channel}
    timetonext = prochaincanard["time"] - time.time()

    if not prochaincanard["channel"]:
        thisDay = now - (now % 86400)
        logger.debug("Plus de canards pour aujourd'hui ! Attente jusqu'a demain (" + str(thisDay + 86400 - time.time()) + " sec)")
        yield from asyncio.sleep(thisDay + 86400 - time.time())
        prochaincanard = yield from  getprochaincanard()
    else:

        logger.debug(
            "Prochain canard : " + str(prochaincanard["time"]) + "(dans " + str(timetonext) + " sec) sur #" + prochaincanard["channel"].name + " - " +
            prochaincanard["channel"].server.name)

    return prochaincanard


@asyncio.coroutine
def mainloop():
    logger.debug("Entrée dans la boucle principale")
    exit_ = False
    prochaincanard = yield from getprochaincanard()
    while not exit_:
        now = time.time()

        if int(now) % 86400 in [0, 1]:
            database.giveBack(logger)

        if int(now) % 60 == 0:
            timetonext = prochaincanard["time"] - now
            logger.debug(
                "Prochain canard : " + str(prochaincanard["time"]) + "(dans " + str(timetonext) + " sec) sur #" + prochaincanard["channel"].name + " - " +
                prochaincanard["channel"].server.name)
            logger.debug("Canards en cours : " + str(canards))

        if prochaincanard["time"] < now:  # CANARD !
            yield from nouveauCanard(prochaincanard)
            prochaincanard = yield from getprochaincanard()

        for canard in canards:
            if int(canard["time"] + tempsAttente) < int(now):  # Canard qui se barre
                logger.debug("Le canard de " + str(canard["time"]) + " est resté trop longtemps, il s'échappe. (il est " + str(
                    int(now)) + ", et il aurait du rester jusqu'a " + str(int(canard["time"] + tempsAttente)) + " )")
                yield from client.send_message(canard["channel"], "Le canard s'échappe.     ·°'\`'°-.,¸¸.·°'\`")
                canards.remove(canard)
        yield from asyncio.sleep(1)


@client.async_event
def on_ready():
    logger.info("Connecté comme " + str(client.user.name) + " | " + str(client.user.id))
    logger.info("Creation de la planification")
    yield from planifie()
    logger.info("Lancers de canards planifiés")
    logger.info("Initialisation terminée :) Ce jeu, ca va faire un carton !")
    yield from mainloop()


@client.async_event
def on_message(message):
    if message.author == client.user:
        return

    if int(message.channel.id) not in whitelist:
        return

    if message.content.startswith('!bang'):
        logger.debug("> BANG (" + str(message.author) + ")")
        now = time.time()
        if database.getStat(message.channel, message.author, "balles") <= 0:
            yield from client.send_message(message.channel, str(message.author.mention) + " > **CHARGEUR VIDE** | Munitions dans l'arme : " + str(
                database.getStat(message.channel, message.author, "balles")) + "/2 | Chargeurs restants : " + str(
                database.getStat(message.channel, message.author, "chargeurs")) + "/2")
            return
        else:
            database.addToStat(message.channel, message.author, "balles", -1)

        if canards:
            canardencours = None
            for canard in canards:
                if canard["channel"] == message.channel:
                    canardencours = canard
                    break

            if canardencours:

                if random.randint(1, 100) < 75:
                    canards.remove(canardencours)
                    tmp = yield from client.send_message(message.channel, str(message.author.mention) + " > BANG")
                    yield from asyncio.sleep(1)
                    database.addToStat(message.channel, message.author, "canardsTues", 1)
                    database.addToStat(message.channel, message.author, "exp", 10)
                    yield from client.edit_message(tmp, str(message.author.mention) + " > :skull_crossbones: **BOUM**\tTu l'as eu en " + str(
                        int(now - canardencours["time"])) + " secondes, ce qui te fait un total de " + str(
                        database.getStat(message.channel, message.author, "canardsTues")) + " canards sur #" + str(
                        message.channel) + ".     \_X<   *COUAC*   [10 xp]")
                    if database.getStat(message.channel, message.author, "meilleurTemps") > int(now - canardencours["time"]):
                        database.setStat(message.channel, message.author, "meilleurTemps", int(now - canardencours["time"]))




                else:
                    tmp = yield from client.send_message(message.channel, str(message.author.mention) + " > BANG")
                    yield from asyncio.sleep(1)
                    yield from client.edit_message(tmp, str(message.author.mention) + " > **PIEWW**\tTu à raté le canard ! [raté : -1 xp]")
                    database.addToStat(message.channel, message.author, "tirsManques", 1)
                    database.addToStat(message.channel, message.author, "exp", -1)
            else:
                yield from client.send_message(message.channel, str(
                    message.author.mention) + " > Par chance tu as raté, mais tu visais qui au juste ? Il n'y a aucun canard dans le coin...   [raté : -1 xp] [tir sauvage : -1 xp]")
                database.addToStat(message.channel, message.author, "tirsSansCanards", 1)
                database.addToStat(message.channel, message.author, "exp", -2)
        else:
            yield from client.send_message(message.channel, str(
                message.author.mention) + " > Par chance tu as raté, mais tu visais qui au juste ? Il n'y a aucun canard dans le coin...   [raté : -1 xp] [tir sauvage : -1 xp]")
            database.addToStat(message.channel, message.author, "tirsSansCanards", 1)
            database.addToStat(message.channel, message.author, "exp", -2)

    elif message.content.startswith("!reload"):
        if database.getStat(message.channel, message.author, "balles") <= 0:
            if database.getStat(message.channel, message.author, "chargeurs") > 0:
                database.setStat(message.channel, message.author, "balles", 2)
                database.addToStat(message.channel, message.author, "chargeurs", -1)
                yield from client.send_message(message.author, str(message.author.mention) + " > Tu recharges ton arme. | Munitions dans l'arme : " + str(
                    database.getStat(message.channel, message.author, "balles")) + "/2 | Chargeurs restants : " + str(
                    database.getStat(message.channel, message.author, "chargeurs")) + "/2")
            else:
                yield from client.send_message(message.author,
                                               str(message.author.mention) + " > Tu es à court de munitions. | Munitions dans l'arme : " + str(
                                                   database.getStat(message.channel, message.author, "balles")) + "/2 | Chargeurs restants : " + str(
                                                   database.getStat(message.channel, message.author, "chargeurs")) + "/2")

        else:
            yield from client.send_message(message.author,
                                           str(message.author.mention) + " > Ton arme n'a pas besoin d'etre rechargée | Munitions dans l'arme : " + str(
                                               database.getStat(message.channel, message.author, "balles")) + "/2 | Chargeurs restants : " + str(
                                               database.getStat(message.channel, message.author, "chargeurs")) + "/2")

    elif message.content.startswith("-,,.-"):
        yield from client.send_message(message.channel, str(
            message.author.mention) + " > Tu as tendu un drapeau de canard et tu t'es fait tirer dessus. Too bad ! [-1 exp]")
        database.addToStat(message.channel, message.author, "exp", -1)

    elif message.content.startswith('!ping'):
        logger.debug("> PING (" + str(message.author) + ")")
        tmp = yield from client.send_message(message.channel, 'BOUM')
        yield from asyncio.sleep(4)
        yield from client.edit_message(tmp, '... Oups ! Pardon, pong !')

    elif message.content.startswith("!duckstat"):
        logger.debug("> DUCKSTATS (" + str(message.author) + ")")

        args_ = message.content.split(" ")
        if len(args_) == 1:
            target = message.author
        else:
            target = message.channel.server.get_member_named(args_[1])
            if target is None:
                target = message.channel.server.get_member(args_[1])
                if target is None:
                    yield from client.send_message(message.author, str(message.author.mention) + " > Je ne reconnais pas cette personne :x")
                    return

        yield from client.send_message(message.author, str(message.author.mention) + " > Statistiques : \n" \
                                                                                      "Canards tués : " + str(
            database.getStat(message.channel, target, "canardsTues")) + "\n" \
                                                                        "Tirs manqués : " + str(
            database.getStat(message.channel, target, "tirsManques")) + "\n" \
                                                                        "Experience : " + str(database.getStat(message.channel, target, "exp")) + "\n" \
                                                                                                                                                  "Tirs sans canards : " + str(
            database.getStat(message.channel, target, "tirsSansCanards")) + "\n" \
                                                                            "Balles : " + str(database.getStat(message.channel, target, "balles")) + "\n" \
                                                                                                                                                     "Chargeurs : " + str(
            database.getStat(message.channel, target, "chargeurs")) + "\n" \
            "Meilleur Temps : " + str(
                    database.getStat(message.channel, target, "meilleurTemps")) )

    elif message.content.startswith("!coin"):
        logger.debug("> COIN (" + str(message.author) + ")")

        if int(message.author.id) in admins:
            yield from nouveauCanard({"channel": message.channel, "time": int(time.time())})
        else:
            yield from client.send_message(message.channel, str(message.author.mention) + " > Oupas (Permission Denied)")

    elif message.content.startswith("!giveback"):
        logger.debug("> GIVEBACK (" + str(message.author) + ")")

        if int(message.author.id) in admins:
            yield from client.send_message(message.author, str(message.author.mention) + " > En cours...")
            database.giveBack(logger)
            yield from client.send_message(message.author, str(message.author.mention) + " > Terminé. Voir les logs sur la console ! ")
        else:
            yield from client.send_message(message.author, str(message.author.mention) + " > Oupas (Permission Denied)")

    elif message.content.startswith("!aide") or message.content.startswith("!help"):
        yield from client.send_message(message.author, aideMsg)

    elif message.content.startswith("!info"):
        logger.debug("INFO (" + str(message.author) + ")")
        yield from client.send_message(message.channel, ":robot: Channel object " + str(
            message.channel) + " ID : " + message.channel.id + " | NAME : " + message.channel.name)
        yield from client.send_message(message.channel,
                                       ":robot: Author  object " + str(message.author) + " ID : " + message.author.id + " | NAME : " + message.author.name)

    elif message.content.startswith("!shop"):
        logger.debug("> SHOP (" + str(message.author) + ")")
        args_ = message.content.split(" ")
        if len(args_) == 1:
            yield from client.send_message(message.channel,  str(message.author.mention) + " > Tu dois préciser le numéro de l'item à acheter aprés cette commande. `!shop [N° item]`")
            return
        else:
            try:
                item = int(args_[1])
            except ValueError:
                yield from client.send_message(message.channel,  str(message.author.mention) + " > Tu dois préciser le numéro de l'item à acheter aprés cette commande. Le numéro donné n'est pas valide. `!shop [N° item]`")
                return

        if item == 1:
            if database.getStat(message.channel, message.author, "balles") < 2:
                if database.getStat(message.channel, message.author, "exp") > 7:
                    yield from client.send_message(message.channel,  str(message.author.mention) + " > Tu ajoutes une balle dans ton arme pour 7 points d'experience")
                    database.addToStat(message.channel, message.author, "balles", 1)
                    database.addToStat(message.channel, message.author, "exp", -7)
                else:
                    yield from client.send_message(message.channel,  str(message.author.mention) + " > Tu n'as pas assez d'experience pour effectuer cet achat ! !")

            else:
                yield from client.send_message(message.channel,  str(message.author.mention) + " > Ton chargeur est déjà plein !")

        elif item == 2:
            if database.getStat(message.channel, message.author, "chargeurs") < 2:
                if database.getStat(message.channel, message.author, "exp") > 13:
                    yield from client.send_message(message.channel,  str(message.author.mention) + " > Tu ajoutes un chargeur à ta réserve pour 13 points d'experience")
                    database.addToStat(message.channel, message.author, "chargeurs", 1)
                    database.addToStat(message.channel, message.author, "exp", -13)
                else:
                    yield from client.send_message(message.channel,  str(message.author.mention) + " > Tu n'as pas assez d'experience pour effectuer cet achat ! !")

            else:
                yield from client.send_message(message.channel,  str(message.author.mention) + " > Ta réserve de chargeurs est déjà pleine !")



client.run(token)
