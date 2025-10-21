from loguru import logger
from mable.cargo_bidding import TradingCompany
from mable.examples import environment, fleets
from mable.transport_operation import ScheduleProposal
from mable.transport_operation import Bid

class MyCompany(TradingCompany):
    def pre_inform(self, trades, time):
        pass

    def inform(self, trades, *args, **kwargs):
        proposed_scheduling = self.propose_schedules(trades)
        scheduled_trades = proposed_scheduling.scheduled_trades
        trades_and_costs = [
            (x, proposed_scheduling.costs[x]) if x in proposed_scheduling.costs
            else (x, 0)
            for x in scheduled_trades]
        bids = [Bid(amount=cost, trade=one_trade) for one_trade, cost in trades_and_costs]
        return bids

    def receive(self, contracts, auction_ledger=None, *args, **kwargs):
        trades = [one_contract.trade for one_contract in contracts]
        scheduling_proposal = self.propose_schedules(trades)
        rejected_trades = self.apply_schedules(scheduling_proposal.schedules)
        if len(rejected_trades) > 0:
            logger.error(f"{len(rejected_trades)} rejected trades.")

    def propose_schedules(self, trades):
        schedules = {}
        costs = {}
        scheduled_trades = []
        i = 0
        while i < len(trades):
            current_trade = trades[i]
            is_assigned = False
            j = 0
            while j < len(self._fleet) and not is_assigned:
                current_vessel = self.fleet[j]
                current_vessel_schedule = schedules.get(current_vessel, current_vessel.schedule)
                new_schedule = current_vessel_schedule.copy()
                new_schedule.add_transportation(current_trade)
                if new_schedule.verify_schedule():
                    loading_time = current_vessel.get_loading_time(current_trade.cargo_type,current_trade.amount)
                    loading_costs = current_vessel.get_loading_consumption(loading_time)
                    unloading_costs = current_vessel.get_unloading_consumption(loading_time)
                    travel_distance = self.headquarters.get_network_distance(current_trade.origin_port,current_trade.destination_port)
                    travel_time = current_vessel.get_travel_time(travel_distance)
                    travel_cost = current_vessel.get_laden_consumption(travel_time,current_vessel.speed)
                    costs[current_trade] = loading_costs + unloading_costs + travel_cost
                    schedules[current_vessel] = new_schedule
                    scheduled_trades.append(current_trade)
                    is_assigned = True
                j += 1
            i += 1
        return ScheduleProposal(schedules, scheduled_trades, costs)

if __name__ == '__main__':
    specifications_builder = environment.get_specification_builder(
        environment_files_path=".",
        trade_occurrence_frequency=40,
        trades_per_occurrence=1,
        num_auctions=4,
        use_only_precomputed_routes=True
    )
    fleet = fleets.example_fleet_1()
    specifications_builder.add_company(MyCompany.Data(MyCompany, fleet, "My Shipping Corp Ltd22."))
    sim = environment.generate_simulation(specifications_builder)
    sim.run()
