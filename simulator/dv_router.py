"""
Your awesome Distance Vector router for CS 168

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

import sim.api as api
from cs168.dv import (
    RoutePacket,
    Table,
    TableEntry,
    DVRouterBase,
    Ports,
    FOREVER,
    INFINITY,
)


class DVRouter(DVRouterBase):

    # A route should time out after this interval
    ROUTE_TTL = 15

    # -----------------------------------------------
    # At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # Determines if you send poison for expired routes
    POISON_EXPIRED = False

    # Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = False

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (
            self.SPLIT_HORIZON and self.POISON_REVERSE
        ), "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        self.ports = Ports()

        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self

        ##### Begin Stage 10A #####

        # Neue Datenstruktur: Speichern der letzten gesendeten Routen
        self.history = {}  # Struktur: {port: {dst: latency}}

        ##### End Stage 10A #####

    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."

        ##### Begin Stage 1 #####

        # da tabelle immutable setzten wir eine neue auf
        # dafür benötigen wir: "dst", "port", "latency", "expire_time"

        # get latency and set expiretime 
        latency = self.ports.get_latency(port)
        expire_time = FOREVER

        # neue TabellenEntry
        new_entry = TableEntry(dst=host, port=port, latency=latency, expire_time=expire_time)
        # neue Tabelle
        new_table = Table()

        # Werte für "schlüssel" im dictionary hinzufügen
        for dst, entry in self.table.items():
            new_table[dst] = entry  # Kopieren der Einträge

        # Füge die neue statische Route hinzu.
        new_table[host] = new_entry

        # Setze die neue Tabelle als aktuelle Tabelle.
        self.table = new_table
        ##### End Stage 1 #####

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        
        ##### Begin Stage 2 #####

        ### check ob destination vorhanden
        dest = packet.dst
        entry = self.table.get(dest, None)  # wenn nichts gefunden wird return NONE
        
        # If no route destination: drop the packet (do nothing)
        if entry is None:
            return
        
        ### Check the latency for the outgoing port
        # If the route is valid, forward the packet to the correct port
        if entry.latency >= INFINITY:
            return
        
        # actual forwarding of the packet to the correct port
        self.send(packet, port = entry.port) #oder: self.send(packet, port = in_port)

        ##### End Stage 2 #####

    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        """
        
        ##### Begin Stages 3, 6, 7, 8, 10 #####

        for port in self.ports.get_all_ports():
                if single_port is not None and port != single_port:
                    continue  # Nur den spezifischen Port behandeln, wenn single_port gesetzt ist

                # Verarbeite jede Route
                for dst, entry in self.table.items():
                    
                    # Split Horizon
                    if self.SPLIT_HORIZON and entry.port == port:
                        continue  # Überspringe

                    # Poison Reverse
                    if self.POISON_REVERSE and entry.port == port:
                        self.send_route_if_needed(port, dst, INFINITY, force)
                    else:
                        advertised_latency = min(entry.latency, INFINITY)
                        self.send_route_if_needed(port, dst, advertised_latency, force)

        ##### End Stages 3, 6, 7, 8, 10 #####

    ####################
    ## START Helpers  ##
    ####################
    def send_route_if_needed(self, port, dst, latency, force):
        """
        Helper method to send route if it hasn't been sent before or if the
        latency has changed. Also updates the history.
        """
        if port not in self.history:
            self.history[port] = {}
        
        if force or self.history[port].get(dst) != latency:
            self.send_route(port, dst, latency)
            self.history[port][dst] = latency

    ####################
    ##  END Helpers   ##
    ####################



    def expire_routes(self):
        """
        Clears out expired routes from table.
        accordingly.
        """
        
        ##### Begin Stages 5, 9 #####

        # Hole die aktuelle Zeit
        current_time = api.current_time()
    
        expired_routes = []
        
        for dest, entry in self.table.items():
            if entry.expire_time <= current_time:
                expired_routes.append(dest)
        
        # auf unendlich setzten
        if self.POISON_EXPIRED:
            for dest in expired_routes:

                new_entry = TableEntry(
                    dst=dest,
                    port=entry.port,  
                    latency=INFINITY,  
                    expire_time=current_time + self.ROUTE_TTL  
                )

                self.table[dest] = new_entry  # Ersetzen d. alten Eintrags

                # Log-Nachricht für Poisoned Route
                self.s_log(f"Route to {dest} has expired and is replaced with poison (INFINITY).")

        # Löschen
        else:
            for dest in expired_routes:
                self.table.pop(dest)

                # Log-Nachricht für abgelaufene Routen
                self.s_log(f"Route to {dest} has expired and is removed.")
                
        ##### End Stages 5, 9 #####

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        """
        
        ##### Begin Stages 4, 10 #####

         # Berechne die Gesamtlatenz (Latenz des Ports + beworbene Latenz)
        total_latency = self.ports.get_latency(port) + route_latency

        # Check / Get entry for specific dest
        entry_for_dest = self.table.get(route_dst, None)

        # Regel 1: Wenn das Ziel nicht in der Tabelle ist, füge es hinzu
        if entry_for_dest is None:
            new_entry = TableEntry(dst=route_dst, port=port, latency=total_latency, expire_time=api.current_time() + self.ROUTE_TTL)
            self.table[route_dst] = new_entry

        # Regel 2: Wenn die Route vom aktuellen Next-Hop kommt, immer akzeptieren
        elif entry_for_dest.port == port:
            new_entry = TableEntry(dst=route_dst, port=port, latency=total_latency, expire_time=api.current_time() + self.ROUTE_TTL)
            self.table[route_dst] = new_entry

        # Regel 3: Wenn Route über anderen Port kommt, nur akzeptieren, wenn sie besser ist
        elif total_latency < entry_for_dest.latency:
            new_entry = TableEntry(dst=route_dst, port=port, latency=total_latency, expire_time=api.current_time() + self.ROUTE_TTL)
            self.table[route_dst] = new_entry

        # Sende die aktualisierten Routen (force=False)
        self.send_routes(force=False)

        ##### End Stages 4, 10 #####

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.ports.add_port(port, latency)

        ##### Begin Stage 10B #####

        # Füge den neuen Port hinzu
        self.ports.add_port(port, latency)

        # Sende sofort Routen, falls self.SEND_ON_LINK_UP aktiviert ist
        if self.SEND_ON_LINK_UP:
            # Sende alle Routen nur an den neuen Port
            self.send_routes(single_port=port)

        ##### End Stage 10B #####

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router goes down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        if port in self.ports.get_all_ports():
            self.ports.remove_port(port)
        else:
            # Optional: Log-Meldung, um darauf hinzuweisen, dass der Port bereits entfernt wurde
            self.s_log(f"Port {port} does not exist.")

        # Liste der Ziele, deren Routen über diesen Port gehen
        routes_to_update = []

        # Iteriere über die Tabelle, um betroffene Routen zu finden
        for dst, entry in self.table.items():
            if entry.port == port:
                routes_to_update.append(dst)

        if self.POISON_ON_LINK_DOWN:
            # Poison: Setze die betroffenen Routen auf INFINITY
            for dst in routes_to_update:
                new_entry = TableEntry(dst=dst, port=port, latency=INFINITY, expire_time=api.current_time() + self.ROUTE_TTL)
                self.table[dst] = new_entry
            
            # Sofort alle Nachbarn über die Poisoned Routes informieren
            self.send_routes(force=True)
        else:
            # Lösche die betroffenen Routen
            for dst in routes_to_update:
                self.table.pop(dst)

            # Optional: Log-Nachricht für entfernte Routen
            self.s_log(f"Routes via port {port} have been removed.")

        ##### End Stage 10B #####

    # Feel free to add any helper methods!
