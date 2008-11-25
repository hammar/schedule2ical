#!/usr/bin/env python

import logging
import os
import wsgiref.handlers

from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

class MainHandler(webapp.RequestHandler):

  def get(self):
    if self.request.query_string:
      try:
        template_values = {
          'schedule': self.getSchedule(self.request.query_string),
        }
        path = os.path.join(os.path.dirname(__file__), 'ical.html')
        self.response.headers['Content-Type'] = 'text/calendar'
        self.response.out.write(template.render(path, template_values))
      except Exception, inst:
        exception_template_values = {
          'exception': type(inst),
          'message': inst,
        }
        path = os.path.join(os.path.dirname(__file__), 'exception.html')
        self.response.out.write(template.render(path, exception_template_values))        
    else:
      path = os.path.join(os.path.dirname(__file__), 'index.html')
      self.response.out.write(template.render(path, {}))

  def getSchedule(self, QueryString):
    baseURL = "http://schema.hj.se/csv.php?"
    csv = self.getCSV(baseURL + QueryString)
    schedule = self.parseCSV(csv)
    return schedule

  def getCSV(self, URL):
    try:
      result = urlfetch.fetch(URL)
      if result.status_code != 200:
        raise urlfetch.Error("HTTP status code %s." % result.status_code)
    except urlfetch.Error, inst:
      logging.error("There was an error retrieving schedule from schema.hj.se: %s" % inst)
      raise
    return result.content

  def parseCSV(self, CSV):
    schedule = []
    rows = CSV.split("\n")
    # Iterate through each row in the CSV file.
    for i in range (2, len(rows)-1):
      columns = rows[i].split(";")
      # For each semicolon delimited column;
      if columns[0] != "D":
        # Parse out some data..
        date=columns[1].replace("-","")
        startTime="%sT%s" % (date,columns[2].replace(":","").ljust(6,"0"))
        endTime="%sT%s" % (date,columns[3].replace(":","").ljust(6,"0"))
        # And construct the post dictionary.
        schedulePost = {
          'startTime': startTime,
          'endTime': endTime,
          'programme': columns[4],
          'course': columns[5],
          'room': columns[7],
          'teacher': columns[8],
          'description': columns[9] + ", " + columns[10],
        }
        # After the first iteration there is the possibilty of doubles.
        if (len(schedule)>1):
          # If two successive posts have the same course name, start time and 
          # end time, they are most likely the same, only with several teachers
          # or classrooms.
          # In this case we add the extra teachers or classrooms rather than
          # create redundant posts.
          previousPost = schedule[len(schedule)-1]
          if (schedulePost["startTime"] == previousPost["startTime"] and
              schedulePost["endTime"] == previousPost["endTime"] and
              schedulePost["course"] == previousPost["course"]):
            # append course room to post (teachers not yet supported)
            if (schedulePost["room"] != previousPost["room"]):
              previousPost["room"] += (", " + schedulePost["room"])
          # Otherwise, add the row to the output list.
          else:
            schedule.append(schedulePost)
        # And if this is the first iteration, just append it.
        else:
          schedule.append(schedulePost)
    return schedule

def main():
  application = webapp.WSGIApplication([('/', MainHandler)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
