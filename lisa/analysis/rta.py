# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019, Arm Limited and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from collections import namedtuple

from lisa.analysis.base import AnalysisHelpers, TraceAnalysisBase
from lisa.datautils import df_filter_task_ids
from lisa.trace import TaskID, requires_events
from lisa.utils import memoized

class RTAEventsAnalysis(TraceAnalysisBase):
    """
    Support for RTA events analysis.

    :param trace: input Trace object
    :type trace: lisa.trace.Trace
    """

    name = 'rta'

    RefTime = namedtuple("RefTime", ['kernel', 'user'])

    PhaseWindow = namedtuple("PhaseWindow", ['id', 'start', 'end'])

    def _task_filtered(self, df, task=None):
        if not task:
            return df
        if type(task) is not TaskID:
            task = self.trace.get_task_id(task)
        if task not in self.rtapp_tasks:
            raise ValueError("Task [{}] is not an rt-app task: {}"
                             .format(task, self.rtapp_tasks))

        return df_filter_task_ids(df, [task],
                                  pid_col='__pid', comm_col='__comm')

    @memoized
    def _get_rtapp_tasks(self):
        task_ids = set()
        for evt in self.trace.available_events:
            if not evt.startswith('rtapp_'):
                continue
            df = self.trace.df_events(evt)
            for pid,name in df[['__pid', '__comm']].drop_duplicates().values:
                task_ids.add(TaskID(pid, name))
        return sorted(task_ids)

    @property
    def rtapp_tasks(self):
        return self._get_rtapp_tasks()


###############################################################################
# DataFrame Getter Methods
###############################################################################

    ###########################################################################
    # rtapp_main events related methods
    ###########################################################################

    @requires_events('rtapp_main')
    def df_rtapp_main(self):
        """
        Dataframe of events generated by the rt-app main task.

        :returns: a :class:`pandas.DataFrame` with:

          * A ``__comm`` column: the actual rt-app trace task name
          * A ``__cpu``  column: the CPU on which the task was running at event
                                 generation time
          * A ``__line`` column: the ftrace line numer
          * A ``__pid``  column: the PID of the task
          * A ``data``   column: the data corresponding to the reported event
          * An ``event`` column: the event generated

        The ``event`` column can report these events:

          * ``start``: the start of the rt-app main thread execution
          * ``end``: the end of the rt-app main thread execution
          * ``clock_ref``: the time rt-app gets the clock to be used for logfile entries

        The ``data`` column reports:

          * the base timestamp used for logfile generated event for the ``clock_ref`` event
          * ``NaN`` for all the other events

        """
        return self.trace.df_events('rtapp_main')

    @property
    @df_rtapp_main.used_events
    def rtapp_window(self):
        """
        Return the time range the rt-app main thread executed.

        :returns: a tuple(start_time, end_time)
        """
        df = self.df_rtapp_main()
        return (
            df[df.event == 'start'].index.values[0],
            df[df.event == 'end'].index.values[0])

    @property
    @df_rtapp_main.used_events
    def rtapp_reftime(self):
        """
        Return the tuple representing the ``kernel`` and ``user`` timestamp.

        RTApp log events are generated based on a reference timestamp.
        This method allows to know which trace timestamp corresponds to the
        logfile generated timestamps.

        :returns: a namedtuple `RefTime` reporting ``kernel`` and ``user``
                  timestamps.
        """
        df = self.df_rtapp_main()

        return self.RefTime(
            df[df.event == 'clock_ref'].index.values[0],
            df[df.event == 'clock_ref'].data.values[0]
        )

    ###########################################################################
    # rtapp_task events related methods
    ###########################################################################

    @requires_events('rtapp_task')
    def df_rtapp_task(self, task=None):
        """
        Dataframe of events generated by each rt-app generated task.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :returns: a :class:`pandas.DataFrame` with:

          * A ``__comm`` column: the actual rt-app trace task name
          * A ``__cpu``  column: the CPU on which the task was running at event
                                 generation time
          * A ``__line`` column: the ftrace line numer
          * A ``__pid``  column: the PID of the task
          * An ``event`` column: the event generated

        The ``event`` column can report these events:

          * ``start``: the start of the ``__pid``:``__comm`` task execution
          * ``end``: the end of the ``__pid``:``__comm`` task execution

        """
        df = self.trace.df_events('rtapp_task')
        return self._task_filtered(df, task)

    ###########################################################################
    # rtapp_loop events related methods
    ###########################################################################

    @requires_events('rtapp_loop')
    def df_rtapp_loop(self, task=None):
        """
        Dataframe of events generated by each rt-app generated task.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :returns: a :class:`pandas.DataFrame` with:

          * A  ``__comm`` column: the actual rt-app trace task name
          * A  ``__cpu``  column: the CPU on which the task was running at event
                                 generation time
          * A  ``__line`` column: the ftrace line numer
          * A  ``__pid``  column: the PID of the task
          * An ``event``  column: the generated event
          * A  ``phase``  column: the phases counter for each ``__pid``:``__comm`` task
          * A  ``phase_loop``  colum: the phase_loops's counter
          * A  ``thread_loop`` column: the thread_loop's counter

        The ``event`` column can report these events:

          * ``start``: the start of the ``__pid``:``__comm`` related event
          * ``end``: the end of the ``__pid``:``__comm`` related event

        """
        df = self.trace.df_events('rtapp_loop')
        return self._task_filtered(df, task)

    @df_rtapp_loop.used_events
    def _get_rtapp_phases(self, event, task):
        df = self.df_rtapp_loop(task)
        df = df[df.event == event]

        # Sort START/END phase loop event from newers/older and...
        if event == 'start':
            df = df[df.phase_loop == 0]
        elif event == 'end':
            df = df.sort_values(by=['phase_loop', 'thread_loop'],
                                ascending=False)
        # ... keep only the newest/oldest event
        df = df.groupby(['__comm', '__pid', 'phase', 'event']).head(1)

        # Reorder the index and keep only required cols
        df = (df.sort_index()[['__comm', '__pid', 'phase']]
              .reset_index()
              .set_index(['__comm', '__pid', 'phase']))

        return df

    @memoized
    @_get_rtapp_phases.used_events
    def df_rtapp_phases_start(self, task=None):
        """
        Dataframe of phases end times.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :returns: a :class:`pandas.DataFrame` with:

          * A  ``__comm`` column: the actual rt-app trace task name
          * A  ``__pid``  column: the PID of the task
          * A  ``phase``  column: the phases counter for each ``__pid``:``__comm`` task

        The ``index`` represents the timestamp of a phase end event.
        """
        return self._get_rtapp_phases('start', task)

    @memoized
    @_get_rtapp_phases.used_events
    def df_rtapp_phases_end(self, task=None):
        """
        Dataframe of phases end times.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :returns: a :class:`pandas.DataFrame` with:

          * A  ``__comm`` column: the actual rt-app trace task name
          * A  ``__pid``  column: the PID of the task
          * A  ``phase``  column: the phases counter for each ``__pid``:``__comm`` task

        The ``index`` represents the timestamp of a phase end event.
        """
        return self._get_rtapp_phases('end', task)

    @df_rtapp_phases_start.used_events
    def _get_task_phase(self, event, task, phase):
        task = self.trace.get_task_id(task)
        if event == 'start':
            df = self.df_rtapp_phases_start(task)
        elif event == 'end':
            df = self.df_rtapp_phases_end(task)
        if phase and phase < 0:
            phase += len(df)
        phase += 1 # because of the followig "head().tail()" filter
        return df.loc[task.comm].head(phase).tail(1).Time.values[0]

    @_get_task_phase.used_events
    def df_rtapp_phase_start(self, task, phase=0):
        """
        Start of the specified phase for a given task.

        A negative phase value can be used to count from the oldest, e.g. -1
        represents the last phase.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :param phase: the ID of the phase start to return (default 0)
        :type phase: int

        :returns: the requires task's phase start timestamp
        """
        return self._get_task_phase('start', task, phase)

    @_get_task_phase.used_events
    def df_rtapp_phase_end(self, task, phase=-1):
        """
        End of the specified phase for a given task.

        A negative phase value can be used to count from the oldest, e.g. -1
        represents the last phase.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :param phase: the ID of the phase end to return (default -1)
        :type phase: int

        :returns: the requires task's phase end timestamp
        """
        return self._get_task_phase('end', task, phase)

    @df_rtapp_task.used_events
    def tasks_window(self, task):
        """
        Return the start end end time for the specified task.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`
        """
        task_df = self.df_rtapp_task(task)
        start_time = task_df[task_df.event == "start"].index[0]
        end_time = task_df[task_df.event == "end"].index[0]

        return (start_time, end_time)

    @df_rtapp_phases_start.used_events
    def task_phase_window(self, task, phase):
        """
        Return the window of a requested task phase.

        For the specified ``task`` it returns a tuple with the (start, end)
        time of the requested ``phase``. A negative phase number can be used to
        count phases backward from the last (-1) toward the first.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :param phase: The ID of the phase to consider
        :type phase: int

        :returns: tuple(start_s, end_s)
        """
        phase_start = self.df_rtapp_phase_start(task, phase)
        phase_end = self.df_rtapp_phase_end(task, phase)

        return self.PhaseWindow(phase, phase_start, phase_end)

    @task_phase_window.used_events
    def task_phase_at(self, task, timestamp):
        """
        Return the :class:`PhaseWindow` for the specified task and timestamp.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :param timestamp: the timestamp to get the pahse for
        :type timestamp: int or float

        :returns: the ID of the phase corresponding to the specified timestamp,
                  None if the specified timestamp does not match a phase
        """
        # Last phase is special, compute end time as start + duration
        last_phase_end = self.df_phases('test_task-0').index[-1]
        last_phase_end += float(self.df_phases('test_task-0').iloc[-1].values)
        if timestamp > last_phase_end:
            return None

        phase_id = len(self.df_phases(task)) - \
                   len(self.df_phases(task)[timestamp:]) - 1
        if phase_id < 0:
            return None

        return self.task_phase_window(task, phase_id)


    ###########################################################################
    # rtapp_phase events related methods
    ###########################################################################

    @requires_events('rtapp_event')
    def df_rtapp_event(self, task=None):
        """
        Returns a :class:`pandas.DataFrame` of all the rt-app generated events.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :returns: a :class:`pandas.DataFrame` with:

          * A  ``__comm`` column: the actual rt-app trace task name
          * A  ``__pid``  column: the PID of the task
          * A ``__cpu``  column: the CPU on which the task was running at event
                                 generation time
          * A ``__line`` column: the ftrace line numer
          * A ``type`` column: the type of the generated event
          * A ``desc`` column: the mnemonic type of the generated event
          * A ``id`` column: the ID of the resource associated to the event,
                             e.g. the ID of the fired timer

        The ``index`` represents the timestamp of the event.
        """
        df = self.trace.df_events('rtapp_event')
        return self._task_filtered(df, task)

    ###########################################################################
    # rtapp_stats events related methods
    ###########################################################################

    @memoized
    @requires_events('rtapp_stats')
    def _get_stats(self):
        df = self.trace.df_events('rtapp_stats').copy(deep=True)
        # Add performance metrics column, performance is defined as:
        #             slack
        #   perf = -------------
        #          period - run
        df['perf_index'] = df['slack'] / (df['c_period'] - df['c_run'])

        return df

    @_get_stats.used_events
    def df_rtapp_stats(self, task=None):
        """
        Returns a :class:`pandas.DataFrame` of all the rt-app generated stats.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :returns: a :class:`pandas.DataFrame` with a set of colums representing
        the stats generated by rt-app after each loop.


        .. seealso:: the rt-app provided documentation:
        https://github.com/scheduler-tools/rt-app/blob/master/doc/tutorial.txt

          * A  ``__comm`` column: the actual rt-app trace task name
          * A  ``__pid``  column: the PID of the task
          * A ``__cpu``  column: the CPU on which the task was running at event
                                 generation time
          * A ``__line`` column: the ftrace line numer
          * A ``type`` column: the type of the generated event
          * A ``desc`` column: the mnemonic type of the generated event
          * A ``id`` column: the ID of the resource associated to the event,
                             e.g. the ID of the fired timer

        The ``index`` represents the timestamp of the event.
        """
        df = self._get_stats()
        return self._task_filtered(df, task)

    @memoized
    @df_rtapp_loop.used_events
    def df_phases(self, task):
        """
        Get phases actual start times and durations

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :returns: A :class:`pandas.DataFrame` with index representing the
        start time of a phase and these column:

        * ``duration``: the measured phase duration.
        """
        # Mark for removal all the events that are not the first 'start'
        def keep_first_start(raw):
            if raw.phase_loop:
                return -1
            if raw.event == 'end':
                return -1
            return 0

        loops_df = self.df_rtapp_loop(task)

        # Keep only the first 'start' and the last 'end' event
        # Do that by first setting -1 the 'phase_loop' of all entries which are
        # not the first 'start' event. Then drop the 'event' column so that we
        # can drop all duplicates thus keeping only the last 'end' even for
        # each phase.
        phases_df = loops_df[['event', 'phase', 'phase_loop']].copy()
        phases_df['phase_loop'] = phases_df.apply(keep_first_start, axis=1)
        phases_df = phases_df[['phase', 'phase_loop']]
        phases_df.drop_duplicates(keep='last', inplace=True)

        # Compute deltas and keep only [start..end] intervals, by dropping
        # instead the [end..start] internals
        durations = phases_df.index[1:] - phases_df.index[:-1]
        durations = durations[::2]

        # Drop all 'end' events thus keeping only the first 'start' event
        phases_df = phases_df[::2][['phase']]

        # Append the duration column
        phases_df['duration'] = durations

        return phases_df[['duration']]

    @df_phases.used_events
    def task_phase_windows(self, task):
        """
        Iterate throw the phases of the specified task.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        At each iteration it returns a :class: `namedtuple` reporting:

         * `id` : the iteration ID
         * `start` : the iteration start time
         * `end` : the iteration end time

        :return: an series of phases start end end timestamps.
        """
        for idx, phase in enumerate(self.df_phases(task).itertuples()):
            yield self.PhaseWindow(idx, phase.Index,
                                    phase.Index+phase.duration)

###############################################################################
# Plotting Methods
###############################################################################

    @AnalysisHelpers.plot_method()
    def plot_phases(self, task, axis, local_fig):
        """
        Draw the task's phases colored bands

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`
        """
        phases_df = self.df_phases(task)

        # Compute phases intervals
        bands = [(t, t + phases_df['duration'][t]) for t in phases_df.index]
        for idx, (start, end) in enumerate(bands):
            color = self.get_next_color(axis)
            label = 'Phase_{:02d}'.format(idx)
            axis.axvspan(start, end, alpha=0.1, facecolor=color, label=label)
        axis.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2,), ncol=8)

        if local_fig:
            task = self.trace.get_task_id(task)
            axis.set_title("Task [{}] phases".format(task))

    @AnalysisHelpers.plot_method()
    def plot_perf(self, task, axis, local_fig):
        r"""
        Plot the performance index.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        The perf index is defined as:

        .. math::

            perf_index = \frac{slack}{c_period - c_run}

        where
        - ``c_period``: is the configured period for an activation
        - ``c_run``: is the configured run time for an activation, assuming to
                     run at the maximum frequency and on the maximum capacity
                     CPU.
        - ``slack``: is the measured slack for an activation

        The slack is defined as the different among the activation deadline
        and the actual completion time of the activation.

        The deadline defines also the start of the next activation, thus in
        normal conditions a task activation is always required to complete
        before its deadline.

        The slack is thus a positive value if a task complete before its
        deadline. It's zero when a task complete an activation right at its
        eadline. It's negative when the completion is over the deadline.

        Thus, a performance index in [0..1] range represents activations
        completed within their deadlines. While, the more the performance index
        is negative the more the task is late with respect to its deadline.
        """
        task = self.trace.get_task_id(task)
        axis.set_title('Task [{0:s}] Performance Index'.format(task))
        data = self.df_rtapp_stats(task)[['perf_index',]]
        data.plot(ax=axis, drawstyle='steps-post')
        axis.set_ylim(0, 2)


    @AnalysisHelpers.plot_method()
    def plot_latency(self, task, axis, local_fig):
        """
        Plot the Latency/Slack and Performance data for the specified task.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        .. seealso:: :meth:`plot_perf` for metrics definition.
        """
        task = self.trace.get_task_id(task)
        axis.set_title('Task [{0:s}] (start) Latency and (completion) Slack'
                       .format(task))
        data = self.df_rtapp_stats(task)[['slack', 'wu_lat']]
        data.plot(ax=axis, drawstyle='steps-post')

    @AnalysisHelpers.plot_method()
    def plot_slack_histogram(self, task, axis, local_fig, bins=30):
        """
        Plot the slack histogram.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :param bins: number of bins for the histogram.
        :type bins: int

        .. seealso:: :meth:`plot_perf` for the slack definition.
        """
        task = self.trace.get_task_id(task)
        ylabel = 'slack of "{}"'.format(task)
        series = self.df_rtapp_stats(task)['slack']
        series.hist(bins=bins, ax=axis, alpha=0.4, label=ylabel)
        axis.axvline(series.mean(), linestyle='--', linewidth=2, label='mean')
        axis.legend()

        if local_fig:
            axis.set_title(ylabel)

    @AnalysisHelpers.plot_method()
    def plot_perf_index_histogram(self, task, axis, local_fig, bins=30):
        """
        Plot the perf index histogram.

        :param task: the (optional) rt-app task to filter for
        :type task: int or str or :class:`TaskID`

        :param bins: number of bins for the histogram.
        :type bins: int

        .. seealso:: :meth:`plot_perf` for the perf index definition.

        """
        task = self.trace.get_task_id(task)
        ylabel = 'perf index of "{}"'.format(task)
        series = self.df_rtapp_stats(task)['perf_index']
        mean = series.mean()
        self.get_logger().info('perf index of task "{}": avg={:.2f} std={:.2f}'
                               .format(task, mean, series.std()))

        series.hist(bins=bins, ax=axis, alpha=0.4, label=ylabel)
        axis.axvline(mean, linestyle='--', linewidth=2, label='mean')
        axis.legend()

        if local_fig:
            axis.set_title(ylabel)

# vim :set tabstop=4 shiftwidth=4 textwidth=80 expandtab
