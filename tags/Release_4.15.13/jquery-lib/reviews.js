function Reviews(label, productid, userid){
    this.label = label;
    this.productid = productid;
    this.hidden = false;
    this.groupBy = 'yyyy/m/dd'; //index to perform groupings of reviews (daily))
    if (typeof userid==='undefined') this.userid = 'all';
    else this.userid = userid;
    this.reviews = [];
    this.data = new Object;
    this.reviews_per_page = 6;
    this.calcStats = function(treviews){
        var num_reviews = treviews.length;
        var total_score = 0;
        var ratingspread = {};
        var score = 0;
        
        for (var x=0; x<treviews.length;x++){
            score = parseInt(treviews[x].rating);
            total_score += score;
            if (typeof ratingspread[score]==='undefined')
                ratingspread[score]=1;
            else
                ratingspread[score]+=1;
        }
        var average = total_score/num_reviews;

        return {numrev: num_reviews, avg: Math.floor(average*100)/100, cum: total_score, ratingspread:ratingspread};
    }

    this.deleteReview = function(rid, dateofreview){
    var newreviews = [];
    //super lazy but going to do it this way
    // until i have a better way to delete
    for (var i=0; i<this.reviews.length; i++)
        if (this.reviews[i].reviewid!=rid) newreviews.push(this.reviews[i]);
    this.reviews = newreviews.slice();
    }
    this.editReview = function(rid, revdata, dateofreview){
        if (typeof dateofreview==='undefined')
            rev_index = this.getReview(rid);
        else
            rev_index = this.getReview(rid, dateofreview);

        this.reviews[rev_index].rating = revdata.rating;
        this.reviews[rev_index].comment = revdata.comment;
        //this.reviews[rev_index].dt = revdata.dt;

    }
    this.getReview = function(rid, dateofreview){
        if (typeof dateofreview==='undefined')
            for(var i=0; i<this.reviews.length; i++)
                if (this.reviews[i].reviewid==rid) return i;
        }

    this.filterReviews = function(filters, label){
        var condition = '1==1';
        for (var z in filters){
            currentfilter = filters[z];
            var attribute = currentfilter.type;
            var minval = 0, maxval =0, val = 0;
            if (attribute=="dt" || attribute=="rating") {
                minval = currentfilter.values[0];
                maxval = currentfilter.values[1];
            }
            else
                val = currentfilter.values;

            if (attribute=='rating'){
                condition += " && this.reviews[x]['" + attribute+ "']>=" + minval;
                condition += " && this.reviews[x]['" + attribute+ "']<=" + maxval;
            }
            else if (attribute=='dt'){
                condition += " && new Date(this.reviews[x]['" + attribute+ "']).getTime()>=" + new Date(minval).getTime();
                condition += " && new Date(this.reviews[x]['" + attribute+ "']).getTime()<=" + new Date(maxval).getTime();
            }
            else if (attribute=='userid')
                condition += " && this.reviews[x]['" + attribute + "'] == '" + val + "'";
            else if (attribute=='productid')
                condition += " && this.reviews[x]['" + attribute + "'] == '" + val + "'";
            else if (attribute=='prodthumb')
                condition += " && this.reviews[x]['" + attribute + "'] == '" + val + "'";
            


        }
        if (typeof label==="undefined") var lbl = this.label + '_filtered';
        else var lbl = label;
        
        var filteredreviews = new Reviews(lbl,this.productid);
        for(var x=0;x<this.reviews.length; x++)
            if (eval(condition))
                filteredreviews.addReview(this.reviews[x]);

        return filteredreviews;

    }
    this.rollupReviews = function(){

        var reviewvolumes = new Object;
        for (i in this.review_agg_data){delete this.review_agg_data[i];};
        if (this.reviews.length==0){return;}

        for(x in this.reviews){
            dtindex = new Date(this.reviews[x].dt);
            reviewindex = dtindex.format(this.groupBy);
            if (typeof(reviewvolumes[reviewindex])==='undefined') reviewvolumes[reviewindex] = {reviews:[]}
            reviewvolumes[reviewindex].reviews.push(this.reviews[x]);

        }
        var maxrev=0;
        for (dates in reviewvolumes){
            var statblock = this.calcStats(reviewvolumes[dates].reviews);
            reviewvolumes[dates].numrev = statblock.numrev;
            if (maxrev<statblock.numrev) maxrev=statblock.numrev;
            reviewvolumes[dates].cum = statblock.cum;
            reviewvolumes[dates].avg = statblock.avg;
            reviewvolumes[dates].ratingspread = statblock.ratingspread;
            reviewvolumes[dates].dt = new Date(dates);
            }
        this.data = reviewvolumes;
        this.max_reviews = maxrev;
        var statblock = this.calcStats(this.reviews);
        this.numrev = statblock.numrev;

        this.avg = statblock.avg;
        this.ratingspread = statblock.ratingspread;
    }
    this.sortReviews = function(){
        //this sorts on date and reviewid for collisions
        this.reviews.sort(function(a, b){if ((a.dt - b.dt)==0) return a.reviewid - b.reviewid; else return a.dt - b.dt;});
    }
    this.addReview = function(review){
        //set the overall range of dates (Main View)
        var newrev = {};
        for (prop in review)
            if (review.hasOwnProperty(prop))
                newrev[prop] = review[prop];


        this.reviews.push(newrev);
    }


    this.minDate = function(treviews){
        var day=new Date();
        for(var i=0;i<treviews.length;i++) if (treviews[i].dt<day) day=treviews[i].dt;
        return day;
        }

    this.maxDate = function(treviews){
        var day=treviews[0].dt;
        for(var i=0;i<treviews.length;i++) if (treviews[i].dt>day) day=treviews[i].dt;
        return day;
        }
    this.getReviewsByPage = function(pagenumber){
        for (x=0;x<pagenumber;x++){
            var revs = [];
            for (i=0; i<this.reviews_per_page; i++)
                if (((x*this.reviews_per_page) + i)<this.reviews.length)
                    revs.push(this.reviews[(this.reviews.length - 1) - ((x*this.reviews_per_page) + i )]);
        }
        return revs;
    }


}
