"""Predicts print durations for the Ultimaker given a list of GCode."""

__copyright__ = '(C) 2014 Theo Boyd - creativecommons.org/licenses/by-sa/2.0'

import re
import sys
import math


class Predictor(object):

    """Use GCode to predict the duration of a print. All times in seconds."""

    def __init__(self, gcode):
        self.gcode = gcode
        self.currSpeed = float(0)
        self.curr = {'X': float(0), 'Y': float(0)}
        self.last = {'X': float(0), 'Y': float(0)}
        self.diff = {'X': float(0), 'Y': float(0)}
        self.seen = {'X': False, 'Y': False}
        self.moveExpected = False
        self.ignoreXYCodes = False

        print('Loaded in ' + str(len(self.gcode)) + ' lines.')

    def predict_file_duration(self):
        """Predict print duration of file. Returns time in seconds."""

        file_duration = 0

        for line in self.gcode:
            file_duration += self.predict_line_duration(line)

        return file_duration

    def predict_line_duration(self, line):
        """Predict print duration of a given line. Returns time in seconds."""

        line_duration = 0

        if line[0] == ';':
            # Line is a comment
            return line_duration

        # Pattern to detect a valid GCode (letter followed by numbers)
        pattern = re.compile('([A-Z][0-9]+)')

        matches = pattern.findall(line)

        for match in matches:
            # Go through all valid GCodes in the line...

            line_duration += self.code_to_duration(match, line)

        return line_duration

    def code_to_duration(self, code, line):
        """Convert a valid GCode to a duration. Returns time in seconds."""

        code_duration = 0

        # F-speed has been calculated using an experiment to be in units of
        # millimetres (distance units) per minute.
        # So a 100-side square (400mm distance) at F1000mm/min takes 4 mins.
        if code[0] == 'F':
            self.currSpeed = float(code[1:])

        elif len(code) >= 2 and (code[0:2] == 'G0' or code[0:2] == 'G1'):
            # Move to location
            self.moveExpected = True
            self.ignoreXYCodes = False

        elif len(code) >= 3 and code[0:3] == 'G28':
            # Reset/home extruder, ignore X and Y codes that immediately
            # follow it as it doesn't have a speed component so we cannot
            # estimate duration of this motion
            self.ignoreXYCodes = True

        elif code[0] == 'X':
            code_duration += self.handle_xy_case('X', code, line)

        elif code[0] == 'Y':
            code_duration += self.handle_xy_case('Y', code, line)

        elif code[0] == 'E':
            # Extrusion, does not affect duration, so ignore
            pass

        else:
            self.moveExpected = False
            print('Unknown code: ' + code)

        return code_duration

    def handle_xy_case(self, case, code, line):
        """Helper method to handle seeing an X or Y in the GCode line.

        If this call to this method completes a valid chain of G, X, Y
        or G, Y, X codes then this method will return the calculated
        travel time since the last valid chain.

        """

        time = 0

        if self.ignoreXYCodes:
            return time

        if case == 'X':
            opp_case = 'Y'
        else:
            opp_case = 'X'

        if not self.moveExpected:
            fail('INVALID GCODE: ' + case + '-code before G-code.')

        self.curr[case] = float(code[1:])

        self.diff[case] = abs(self.curr[case] - self.last[case])

        self.last[case] = self.curr[case]

        if self.seen[opp_case]:
            if not self.seen[case]:
                # We've seen the opposite code, and now we have this code
                # clear the flags and perform the calculation

                self.moveExpected = False
                self.seen[opp_case] = False
                self.seen[case] = False

                distance = hypotenuse(self.diff[case], self.diff[opp_case])
                speed = self.currSpeed
                if speed == 0:
                    # Look ahead for an F code

                    pattern = re.compile('(F[0-9]+)')
                    matches = pattern.findall(line)

                    for match in matches:
                        # Take last speed in line
                        speed = float(match[1:])

                    if speed == 0:
                        # If speed is still zero, GCode is invalid
                        fail("INVALID SPEED: Move w/o speed having been set.")

                # F-speed is in mm/s but actually measured it is in mm/min,
                # so we need to multiply by 60
                time = 60 * (distance / speed)

            else:
                # Has seen a other code already -- invalid
                fail('INVALID GCODE: Two ' + case +
                     '-codes with no intervening ' + opp_case + '.')
        else:
            # Mark that we've updated this case and await the opposite one
            self.seen[case] = True

        return time


def fail(error_message):
    """Exit the program due to error given my message."""

    print(error_message)
    sys.exit(-1)


def hypotenuse(side_a, side_b):
    """Return hypotenuse of triangle with sides A and B."""

    return math.sqrt(pow(side_a, 2) + pow(side_b, 2))

if __name__ == '__main__':
    args = sys.argv

    if not len(args) == 2:
        fail('USAGE: python predictor.py <GCODE_FILE_PATH>')

    gcode_file_path = args[1]

    gcode_file = open(gcode_file_path, 'r')
    try:
        gcode_lines = gcode_file.readlines()
    finally:
        gcode_file.close()

    p = Predictor(gcode_lines)
    print(p.predict_file_duration())
